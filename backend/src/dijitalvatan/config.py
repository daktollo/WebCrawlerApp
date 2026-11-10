"""Application settings."""

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = BACKEND_ROOT / "data" / "dijitalvatan.db"
MIGRATIONS_DIR = BACKEND_ROOT / "migrations"
CRAWLER_LOCK_PATH = BACKEND_ROOT / "data" / "crawler.lock"

# API + crawler. Locally only this machine can reach it; the Docker image sets DIJITALVATAN_HOST=0.0.0.0 so the
# frontend container (nginx on port 1319) can proxy /api to it.
HOST = os.environ.get("DIJITALVATAN_HOST", "127.0.0.1")
PORT = 1320

# Seeds the crawl may start from. The www alias of the university redirects to the bare domain.
BOGAZICI_REQUESTED_SEED = "https://www.bogazici.edu.tr/"
BOGAZICI_SEED = "https://bogazici.edu.tr/"
TSK_REQUESTED_SEED = "https://www.tsk.gov.tr/"
TSK_OFFICIAL_SEED = "https://www.tsk.tr/"
DEFAULT_SEED = BOGAZICI_SEED
SEED_ALIASES = {
    BOGAZICI_SEED: BOGAZICI_SEED,
    BOGAZICI_REQUESTED_SEED: BOGAZICI_SEED,
    TSK_REQUESTED_SEED: TSK_REQUESTED_SEED,
    TSK_OFFICIAL_SEED: TSK_OFFICIAL_SEED,
}

DEFAULT_PAGE_LIMIT = 200
MAX_DEPTH = 3
QUEUE_CAPACITY_PER_PAGE = 4  # queue rows allowed per page of the limit

USER_AGENT = "DijitalVatanBot/1.0"
MIN_REQUEST_DELAY_MS = 1500  # global and per-origin minimum spacing between requests
FETCH_TIMEOUT_S = 8
MAX_REDIRECTS = 4
MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_OUTLINKS_PER_PAGE = 300
ROBOTS_CACHE_S = 24 * 60 * 60
RANK_REFRESH_EVERY = 8  # processed pages between PageRank refreshes
IDLE_POLL_S = 5

PAGERANK_DAMPING = 0.8
PAGERANK_ITERATIONS = 10

SEARCH_DEFAULT_LIMIT = 30
SEARCH_MAX_LIMIT = 100
WORDS_DEFAULT_LIMIT = 50
WORDS_MAX_LIMIT = 100
WORD_PREVIEW_PAGES = 5
MAX_QUERY_CHARS = 200
