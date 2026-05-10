import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from besoccer_scraper.infrastructure.db.migrations import MigrationRunner
from besoccer_scraper.infrastructure.db.repositories import PostgresMatchRepository


pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for Postgres integration tests",
)


def test_match_repository_upsert_get_and_count() -> None:
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    MigrationRunner(engine).migrate()

    with Session(engine) as session:
        session.execute(text("TRUNCATE TABLE matches, sources RESTART IDENTITY CASCADE"))
        source_id = int(
            session.execute(
                text("INSERT INTO sources (source_name) VALUES ('besoccer') RETURNING id")
            ).scalar_one()
        )
        session.commit()

        repo = PostgresMatchRepository(session)
        match_id = repo.upsert_match(
            source_id=source_id,
            source_match_id="2022305526",
            payload={"competition": "liga_mx", "season_key": "clausura-2025", "score": "2-1"},
        )
        session.commit()

        updated_id = repo.upsert_match(
            source_id=source_id,
            source_match_id="2022305526",
            payload={"competition": "liga_mx", "season_key": "clausura-2025", "score": "3-1"},
        )
        session.commit()

        assert match_id == updated_id
        stored = repo.get_by_source_match_id(source_id=source_id, source_match_id="2022305526")
        assert stored is not None
        assert stored["source_match_id"] == "2022305526"
        assert stored["payload"]["score"] == "3-1"

        assert repo.count_by_competition_season(competition="liga_mx", season_key="clausura-2025") == 1
