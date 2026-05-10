ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS source_name TEXT DEFAULT 'besoccer';
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS target_type TEXT DEFAULT 'match_page';
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS source_match_id TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS source_competition_slug TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS season_key TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS round_label TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending';
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 100;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS max_attempts INTEGER DEFAULT 3;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS last_error TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS last_http_status INTEGER;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMPTZ;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS locked_by TEXT;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS last_scraped_at TIMESTAMPTZ;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'::jsonb;
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE scrape_targets ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE scrape_targets
SET
    url = COALESCE(url, payload ->> 'url', payload ->> 'source_url'),
    source_match_id = COALESCE(source_match_id, payload ->> 'source_match_id', payload ->> 'match_source_id'),
    source_competition_slug = COALESCE(source_competition_slug, payload ->> 'competition', payload ->> 'competition_slug'),
    season_key = COALESCE(season_key, payload ->> 'season_key', payload ->> 'season'),
    round_label = COALESCE(round_label, payload ->> 'round_label'),
    metadata_json = COALESCE(metadata_json, payload, '{}'::jsonb)
WHERE EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'scrape_targets' AND column_name = 'payload'
);

CREATE INDEX IF NOT EXISTS ix_scrape_targets_status ON scrape_targets(status);
CREATE INDEX IF NOT EXISTS ix_scrape_targets_competition_season ON scrape_targets(source_competition_slug, season_key);
CREATE INDEX IF NOT EXISTS ix_scrape_targets_source_match_id ON scrape_targets(source_match_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_scrape_targets_source_source_match_id ON scrape_targets(source_name, source_match_id) WHERE source_match_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_scrape_targets_source_type_url ON scrape_targets(source_name, target_type, url) WHERE url IS NOT NULL;

ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS source_name TEXT DEFAULT 'besoccer';
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS target_id BIGINT;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS run_id BIGINT;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS http_status INTEGER;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS content_hash TEXT;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS html TEXT;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS response_headers_json JSONB DEFAULT '{}'::jsonb;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS request_metadata_json JSONB DEFAULT '{}'::jsonb;
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE raw_pages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
UPDATE raw_pages SET content_hash = COALESCE(content_hash, body_hash), html = COALESCE(html, body), http_status = COALESCE(http_status, status_code);
CREATE UNIQUE INDEX IF NOT EXISTS ux_raw_pages_source_url_hash ON raw_pages(source_name, url, content_hash);

ALTER TABLE matches ADD COLUMN IF NOT EXISTS source_name TEXT DEFAULT 'besoccer';
ALTER TABLE matches ADD COLUMN IF NOT EXISTS source_match_id TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS url TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS source_competition_slug TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS competition_name TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS season_key TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS round_label TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS match_date_utc TIMESTAMPTZ;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_team_name TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_team_name TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS home_score INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS away_score INTEGER;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS venue TEXT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS stats_json JSONB DEFAULT '{}'::jsonb;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS events_json JSONB DEFAULT '[]'::jsonb;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS raw_page_id BIGINT;
ALTER TABLE matches ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE matches ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE matches ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE matches ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

UPDATE matches
SET
    source_competition_slug = COALESCE(source_competition_slug, payload ->> 'competition_slug', payload ->> 'competition'),
    season_key = COALESCE(season_key, payload ->> 'season_key', payload ->> 'season'),
    round_label = COALESCE(round_label, payload ->> 'round_label'),
    url = COALESCE(url, payload ->> 'url'),
    stats_json = COALESCE(stats_json, payload -> 'stats_json', '{}'::jsonb),
    events_json = COALESCE(events_json, payload -> 'events_json', '[]'::jsonb)
WHERE EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'matches' AND column_name = 'payload'
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_matches_source_source_match_id ON matches(source_name, source_match_id);
