-- Dijital Vatan search engine: crawl state, crawled pages, link graph, inverted index.
-- Lives in its own schema so Supabase's REST API (which exposes only "public") cannot reach it.

CREATE SCHEMA dijitalvatan;

-- Single-row table: there is exactly one active crawl at a time.
CREATE TABLE dijitalvatan.crawl_state (
    id              smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    seed            text,
    status          text NOT NULL DEFAULT 'idle' CHECK (status IN
                    ('idle', 'running', 'paused', 'completed', 'blocked', 'error', 'limit_reached')),
    max_pages       integer NOT NULL DEFAULT 500 CHECK (max_pages BETWEEN 1 AND 500),
    max_depth       integer NOT NULL DEFAULT 3,
    delay_ms        integer NOT NULL DEFAULT 1500,
    current_url     text,
    last_error      text,
    revision        bigint NOT NULL DEFAULT 0,
    started_at      timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now(),
    last_indexed_at timestamptz
);
INSERT INTO dijitalvatan.crawl_state DEFAULT VALUES;

-- Every discovered URL; rows in state 'queued' form the breadth-first crawl queue.
CREATE TABLE dijitalvatan.pages (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    url           text NOT NULL UNIQUE,
    depth         integer NOT NULL,
    state         text NOT NULL CHECK (state IN ('queued', 'indexed', 'failed', 'skipped')),
    title         text,
    description   text,
    error         text,
    discovered_at timestamptz NOT NULL DEFAULT now(),
    processed_at  timestamptz
);
CREATE INDEX pages_queue_idx ON dijitalvatan.pages (state, depth, id);

CREATE TABLE dijitalvatan.links (
    from_page_id bigint NOT NULL REFERENCES dijitalvatan.pages (id) ON DELETE CASCADE,
    to_page_id   bigint NOT NULL REFERENCES dijitalvatan.pages (id) ON DELETE CASCADE,
    PRIMARY KEY (from_page_id, to_page_id)
);
CREATE INDEX links_to_idx ON dijitalvatan.links (to_page_id);

CREATE TABLE dijitalvatan.words (
    id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    word text NOT NULL UNIQUE
);
-- Supports prefix filtering (word LIKE 'abc%') in the word index view.
CREATE INDEX words_prefix_idx ON dijitalvatan.words (word text_pattern_ops);

-- One row per (word, page, field) where the word occurs.
CREATE TABLE dijitalvatan.postings (
    word_id bigint NOT NULL REFERENCES dijitalvatan.words (id) ON DELETE CASCADE,
    page_id bigint NOT NULL REFERENCES dijitalvatan.pages (id) ON DELETE CASCADE,
    field   text   NOT NULL CHECK (field IN ('content', 'title', 'url')),
    PRIMARY KEY (word_id, page_id, field)
);
CREATE INDEX postings_page_idx ON dijitalvatan.postings (page_id);
