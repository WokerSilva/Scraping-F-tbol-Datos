INSERT INTO sources (source_name)
VALUES ('besoccer')
ON CONFLICT (source_name) DO NOTHING;

CREATE UNIQUE INDEX IF NOT EXISTS uq_sources_name ON sources(source_name);
