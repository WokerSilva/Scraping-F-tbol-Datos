import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from besoccer_scraper.infrastructure.db.migrations import MigrationRunner
from besoccer_scraper.infrastructure.db.repositories import PostgresTargetRepository


pytestmark = pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"),
    reason="TEST_DATABASE_URL is required for Postgres integration tests",
)


def test_target_repository_upsert_list_count_and_transitions() -> None:
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    MigrationRunner(engine).migrate()

    with Session(engine) as session:
        session.execute(text("TRUNCATE TABLE scrape_targets RESTART IDENTITY CASCADE"))
        session.commit()

        repo = PostgresTargetRepository(session)
        target_id = repo.upsert_target(
            source_name="besoccer",
            target_type="match",
            url="https://www.besoccer.com/partido/a/b/2022305526",
            source_match_id="2022305526",
            payload={"competition": "liga_mx", "season_key": "clausura-2025", "status": "pending", "round_label": "JORNADA17"},
        )
        session.commit()

        updated_id = repo.upsert_target(
            source_name="besoccer",
            target_type="match",
            url="https://www.besoccer.com/partido/a/b/2022305526",
            source_match_id="2022305526",
            payload={"competition": "liga_mx", "season_key": "clausura-2025", "status": "discovered", "round_label": "JORNADA17"},
        )
        session.commit()

        assert target_id == updated_id
        assert len(repo.list_for_processing(limit=10)) == 1
        assert repo.count_by_competition_season(competition="liga_mx", season_key="clausura-2025") == 1

        assert repo.mark_transition(target_id=target_id, from_statuses=("discovered",), to_status="in_progress") is True
        assert repo.mark_transition(target_id=target_id, from_statuses=("pending",), to_status="parsed") is False
        assert repo.mark_transition(target_id=target_id, from_statuses=("in_progress",), to_status="parsed") is True
        session.commit()

        counts = repo.count_by_status()
        assert counts["parsed"] == 1
