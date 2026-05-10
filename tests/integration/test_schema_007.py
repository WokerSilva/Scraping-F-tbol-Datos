import os
import pytest
from sqlalchemy import text

from besoccer_scraper.bootstrap import build_container
from besoccer_scraper.cli.app import build_parser
from besoccer_scraper.application.db_services import DatabaseService


pytestmark = pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="TEST_DATABASE_URL not set")


def test_schema_007_columns_present() -> None:
    args = build_parser().parse_args(["--database-url", os.environ["TEST_DATABASE_URL"], "db", "status"])
    container = build_container(args)
    DatabaseService(container.db.engine).migrate()
    with container.db.engine.connect() as conn:
        cols = conn.execute(text("""
        SELECT table_name, column_name FROM information_schema.columns
        WHERE table_schema='public' AND (
          (table_name='scrape_targets' AND column_name IN ('status','source_competition_slug','season_key','round_label','metadata_json')) OR
          (table_name='matches' AND column_name IN ('stats_json','events_json')))
        """)).mappings().all()
    found = {(r['table_name'], r['column_name']) for r in cols}
    for pair in [
        ("scrape_targets", "status"),
        ("scrape_targets", "source_competition_slug"),
        ("scrape_targets", "season_key"),
        ("scrape_targets", "round_label"),
        ("scrape_targets", "metadata_json"),
        ("matches", "stats_json"),
        ("matches", "events_json"),
    ]:
        assert pair in found
