CREATE TABLE IF NOT EXISTS raw_pages (
    id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    url TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status_code INTEGER,
    body TEXT NOT NULL,
    body_hash TEXT NOT NULL
);
