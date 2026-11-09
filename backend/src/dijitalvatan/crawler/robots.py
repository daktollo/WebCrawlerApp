"""robots.txt parsing (RFC 9309): the most specific user-agent group wins, longest path rule decides."""

import math
import re
from dataclasses import dataclass, field
from urllib.parse import quote, urlsplit

from dijitalvatan import config

MAX_ROBOTS_CHARS = 512_000
DELAY_VALUE = re.compile(r"^\d+(?:\.\d+)?$")
ESCAPE_OR_NON_ASCII = re.compile(r"%[0-9a-fA-F]{2}|[^\x00-\x7f]+")
UNRESERVED = re.compile(r"^[A-Za-z0-9._~-]$")


@dataclass
class RobotsRule:
    path: str
    allow: bool


@dataclass
class RobotsPolicy:
    rules: list[RobotsRule] = field(default_factory=list)
    delay_ms: int = field(default_factory=lambda: config.MIN_REQUEST_DELAY_MS)

    def to_json(self) -> dict:
        return {"rules": [{"path": rule.path, "allow": rule.allow} for rule in self.rules], "delayMs": self.delay_ms}

    @classmethod
    def from_json(cls, value: dict) -> "RobotsPolicy":
        return cls([RobotsRule(rule["path"], rule["allow"]) for rule in value["rules"]], value["delayMs"])

    def allows(self, url: str) -> bool:
        parts = urlsplit(url)
        target = _robots_path(parts.path + (f"?{parts.query}" if parts.query else ""))
        longest = -1
        allowed = True
        for rule in self.rules:
            path = _robots_path(rule.path)
            exact_end = path.endswith("$")
            body = path[:-1] if exact_end else path
            if not _pattern_matches(target, body, exact_end):
                continue
            length = len(re.sub(r"%[0-9A-F]{2}", "x", body.replace("*", "")))
            if length > longest or (length == longest and rule.allow):
                longest = length
                allowed = rule.allow
        return allowed


@dataclass
class _Group:
    agents: list[str] = field(default_factory=list)
    rules: list[RobotsRule] = field(default_factory=list)
    delay_ms: int | None = None
    has_directives: bool = False


def parse_robots(text: str, user_agent: str = "DijitalVatanBot") -> RobotsPolicy:
    groups: list[_Group] = []
    current: _Group | None = None
    for raw in text[:MAX_ROBOTS_CHARS].removeprefix("﻿").splitlines():
        line = raw.split("#", 1)[0].strip()
        key, colon, value = line.partition(":")
        if not colon:
            continue
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            if current is None or current.has_directives:
                current = _Group()
                groups.append(current)
            if value:
                current.agents.append(value.lower())
            continue
        if current is None or key not in ("allow", "disallow", "crawl-delay"):
            continue
        current.has_directives = True
        if key == "crawl-delay":
            if DELAY_VALUE.match(value):
                current.delay_ms = max(current.delay_ms or 0, math.ceil(float(value) * 1000))
        elif value.startswith("/"):
            current.rules.append(RobotsRule(value, key == "allow"))

    agent = user_agent.lower()
    scores = [
        max([-1] + [0 if value == "*" else len(value) if value in agent else -1 for value in group.agents])
        for group in groups
    ]
    policy = RobotsPolicy()
    best = max([-1] + scores)
    if best < 0:
        return policy
    for group, score in zip(groups, scores):
        if score == best:
            policy.rules.extend(group.rules)
            policy.delay_ms = max(policy.delay_ms, group.delay_ms or 0)
    return policy


def _robots_path(value: str) -> str:
    """Reserved escapes stay escaped; UTF-8 text and unreserved escapes compare equal."""

    def canonical(match: re.Match) -> str:
        part = match.group(0)
        if part[0] != "%":
            return quote(part, safe="")
        char = chr(int(part[1:], 16))
        return char if UNRESERVED.match(char) else part.upper()

    return ESCAPE_OR_NON_ASCII.sub(canonical, value)


def _pattern_matches(target: str, pattern: str, exact_end: bool) -> bool:
    """Glob match with '*' wildcards, without compiling site-controlled patterns into regexes."""
    index = pointer = checkpoint = 0
    star = -1
    while index < len(target):
        if pointer == len(pattern) and not exact_end:
            return True
        if pointer < len(pattern) and pattern[pointer] == target[index]:
            pointer += 1
            index += 1
        elif pointer < len(pattern) and pattern[pointer] == "*":
            star = pointer
            pointer += 1
            checkpoint = index
        elif star >= 0:
            pointer = star + 1
            checkpoint += 1
            index = checkpoint
        else:
            return False
    while pointer < len(pattern) and pattern[pointer] == "*":
        pointer += 1
    return pointer == len(pattern)
