# /// script
# requires-python = ">=3.11"
# dependencies = ["websocket-client"]
# ///
"""Run one shell command on the Raspberry Pi through the CasaOS web terminal.

The Pi's SSH port is not forwarded to the internet; CasaOS opens the SSH session
from inside the Pi (127.0.0.1) and bridges it over a WebSocket. This script logs in
to CasaOS, opens that session, runs the command, prints its output and exits with
the remote exit code. `sudo` password prompts are answered with the SSH password.

Usage: uv run casaos_ssh.py "sudo docker ps"
"""
import base64
import json
import re
import secrets
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import websocket

ENV_PATH = Path(__file__).with_name(".env")
COMMAND_TIMEOUT_S = 1800
PROMPT_TIMEOUT_S = 20
TERMINAL_COLS = 250
TERMINAL_ROWS = 50

ANSI_PATTERN = re.compile(r"\x1b(\[[0-9;?]*[ -/]*[@-~]|\][^\x07]*\x07|[()][0-9A-Za-z])")
SUDO_PROMPT = re.compile(r"\[sudo\] password for [^:]+: ?$")


class Credentials:
    def __init__(self, path: Path):
        values = dict(
            line.split("=", 1)
            for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        )
        self.casaos_url = values["CASAOS_URL"].rstrip("/")
        self.casaos_username = values["CASAOS_USERNAME"]
        self.casaos_password = values["CASAOS_PASSWORD"]
        self.ssh_username = values["SSH_USERNAME"]
        self.ssh_password = values["SSH_PASSWORD"]
        self.ssh_port = values["SSH_PORT"]


class CasaosClient:
    def __init__(self, credentials: Credentials):
        self.credentials = credentials

    def login(self) -> str:
        body = json.dumps({
            "username": self.credentials.casaos_username,
            "password": self.credentials.casaos_password,
        }).encode()
        request = urllib.request.Request(
            self.credentials.casaos_url + "/v1/users/login",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        response = json.load(urllib.request.urlopen(request, timeout=15))
        if response.get("success") != 200:
            raise RuntimeError(f"CasaOS login failed: {response.get('message')}")
        return response["data"]["token"]["access_token"]

    def open_terminal(self, token: str) -> websocket.WebSocket:
        query = urllib.parse.urlencode({
            "token": token,
            "username": self.credentials.ssh_username,
            "password": self.credentials.ssh_password,
            "port": self.credentials.ssh_port,
            "cols": TERMINAL_COLS,
            "rows": TERMINAL_ROWS,
        })
        ws_url = self.credentials.casaos_url.replace("http", "ws", 1) + "/v1/sys/wsssh?" + query
        return websocket.create_connection(ws_url, timeout=15)


class RemoteShell:
    def __init__(self, ws: websocket.WebSocket, sudo_password: str):
        self.ws = ws
        self.sudo_password = sudo_password
        self.ws.settimeout(1)

    def _receive(self) -> str:
        try:
            message = self.ws.recv()
        except websocket.WebSocketTimeoutException:
            return ""
        text = message.decode(errors="replace") if isinstance(message, bytes) else message
        return ANSI_PATTERN.sub("", text).replace("\r", "")

    def _read_until(self, pattern: re.Pattern, timeout_s: float, stream: bool = False) -> str:
        buffer, deadline = "", time.time() + timeout_s
        while not pattern.search(buffer):
            if time.time() > deadline:
                raise TimeoutError(f"no {pattern.pattern!r} within {timeout_s}s; last output:\n{buffer[-2000:]}")
            chunk = self._receive()
            buffer += chunk
            if SUDO_PROMPT.search(buffer):
                buffer = SUDO_PROMPT.sub("", buffer)
                self.ws.send(self.sudo_password + "\n")
            if stream and chunk:
                sys.stdout.write(chunk)
                sys.stdout.flush()
        return buffer

    def run(self, command: str) -> int:
        self._read_until(re.compile(r"\$ $"), PROMPT_TIMEOUT_S)
        tag = secrets.token_hex(4)
        begin = re.compile(rf"__BEGIN_{tag}__\n")
        end = re.compile(rf"__END_{tag}__(\d+)\n")
        # Silence echo and prompts so only the command's own output reaches the markers.
        self.ws.send(
            "stty -echo; PS1=''; PS2=''; PROMPT_COMMAND=''; "
            f"export TERM=dumb PAGER=cat GIT_PAGER=cat SYSTEMD_PAGER=cat; printf '__BEGIN_%s__\\n' {tag}\n"
        )
        self._read_until(begin, PROMPT_TIMEOUT_S)
        # One input line only: anything queued on the terminal after the command
        # would be read by sudo as the password.
        encoded = base64.b64encode(command.encode()).decode()
        self.ws.send(f"eval \"$(printf %s {encoded} | base64 -d)\"; printf '__END_%s__%s\\n' {tag} \"$?\"\n")
        output = self._read_until(end, COMMAND_TIMEOUT_S)
        sys.stdout.write(end.split(output)[0])
        self.ws.send("exit\n")
        self.ws.close()
        return int(end.search(output).group(1))


def main() -> None:
    command = sys.argv[1]
    credentials = Credentials(ENV_PATH)
    client = CasaosClient(credentials)
    shell = RemoteShell(client.open_terminal(client.login()), credentials.ssh_password)
    sys.exit(shell.run(command))


if __name__ == "__main__":
    main()
