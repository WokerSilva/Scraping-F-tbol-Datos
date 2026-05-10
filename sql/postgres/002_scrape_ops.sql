CREATE TABLE IF NOT EXISTS scrape_targets (
    id BIGSERIAL PRIMARY KEY,
    source_name TEXT NOT NULL,
    target_type TEXT NOT NULL,
    url TEXT NOT NULL,
    source_match_id TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
