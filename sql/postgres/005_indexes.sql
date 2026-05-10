ALTER TABLE scrape_targets
    ADD CONSTRAINT uq_scrape_targets_source_target_url
    UNIQUE (source_name, target_type, url);

CREATE UNIQUE INDEX IF NOT EXISTS uq_scrape_targets_source_match_not_null
    ON scrape_targets (source_name, source_match_id)
    WHERE source_match_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_raw_pages_source_url ON raw_pages(source_name, url);
