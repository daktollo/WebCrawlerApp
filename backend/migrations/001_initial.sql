-- Dijital Vatan search engine: crawl state, URL queue, per-site politeness, indexed pages, link graph, inverted index.
-- There is exactly one crawl at a time; starting from a new seed clears every table except crawl_state and
-- the pending Retry-After times in origins.
-- Timestamps are ISO-8601 UTC text ("2026-11-10T09:30:00.000Z"); *_ms columns are Unix epoch milliseconds.

CREATE TABLE crawl_state (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    seed          TEXT,
    status        TEXT    NOT NULL DEFAULT 'idle' CHECK (status IN
                  ('idle', 'running', 'paused', 'completed', 'blocked', 'error', 'limit_reached')),
    max_pages     INTEGER NOT NULL DEFAULT 200 CHECK (max_pages >= 1),
    max_depth     INTEGER NOT NULL DEFAULT 3,
    current_url   TEXT,
    last_error    TEXT,
    -- Bumped on every change clients should notice; never decreases, even across resets.
    revision      INTEGER NOT NULL DEFAULT 0,
    indexed_words INTEGER NOT NULL DEFAULT 0,
    -- Identifies one crawl generation: a reset gives it a new, strictly later value.
    started_at    TEXT,
    updated_at    TEXT
);
INSERT INTO crawl_state (id) VALUES (1);

-- robots.txt policy, request spacing and access blocks, kept per site (scheme + host).
CREATE TABLE origins (
    origin               TEXT PRIMARY KEY,
    robots_policy        TEXT,
    robots_checked_at_ms INTEGER,
    delay_ms             INTEGER NOT NULL DEFAULT 1500,
    next_request_at_ms   INTEGER NOT NULL DEFAULT 0,
    blocked_reason       TEXT,
    blocked_phase        TEXT CHECK (blocked_phase IN ('error', 'blocked'))
);

-- Every discovered URL; 'queued' rows are crawled breadth-first (depth, then discovery order).
CREATE TABLE queue (
    id         INTEGER PRIMARY KEY,
    url        TEXT    NOT NULL UNIQUE,
    origin     TEXT    NOT NULL,
    depth      INTEGER NOT NULL,
    state      TEXT    NOT NULL DEFAULT 'queued' CHECK (state IN ('queued', 'done', 'skipped', 'failed')),
    error      TEXT,
    updated_at TEXT    NOT NULL
);
CREATE INDEX queue_next_idx ON queue (state, depth, id);
CREATE INDEX queue_errors_idx ON queue (updated_at) WHERE error IS NOT NULL;

-- Indexed pages under their final URL (after redirects).
CREATE TABLE pages (
    id          INTEGER PRIMARY KEY,
    url         TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    body        TEXT NOT NULL,
    rank        REAL NOT NULL DEFAULT 0,
    indexed_at  TEXT NOT NULL
);
CREATE INDEX pages_rank_idx ON pages (rank DESC, url);
CREATE INDEX pages_indexed_at_idx ON pages (indexed_at);

-- Outlinks of an indexed page; the target may or may not be indexed itself.
CREATE TABLE links (
    source_id  INTEGER NOT NULL REFERENCES pages (id) ON DELETE CASCADE,
    target_url TEXT    NOT NULL,
    PRIMARY KEY (source_id, target_url)
) WITHOUT ROWID;
CREATE INDEX links_target_idx ON links (target_url);

CREATE TABLE words (
    id   INTEGER PRIMARY KEY,
    word TEXT NOT NULL UNIQUE
);

-- One row per (word, page, field) where the normalized word occurs.
CREATE TABLE postings (
    word_id INTEGER NOT NULL REFERENCES words (id) ON DELETE CASCADE,
    page_id INTEGER NOT NULL REFERENCES pages (id) ON DELETE CASCADE,
    field   TEXT    NOT NULL CHECK (field IN ('content', 'title', 'url')),
    PRIMARY KEY (word_id, page_id, field)
) WITHOUT ROWID;
CREATE INDEX postings_page_idx ON postings (page_id);
