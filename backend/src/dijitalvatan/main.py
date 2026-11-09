"""Start the server: API, background crawler and (when built) the frontend on http://HOST:PORT.

Run: uv run python -m dijitalvatan.main
"""

import logging

import uvicorn

from dijitalvatan import config


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # One worker: the crawler runs inside the server process.
    uvicorn.run("dijitalvatan.api.app:app", host=config.HOST, port=config.PORT, workers=1)


if __name__ == "__main__":
    main()
