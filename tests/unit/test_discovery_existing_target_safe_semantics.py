import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from besoccer_scraper.infrastructure.db.repositories import PostgresTargetRepository


class _ResultExisting:
    def mappings(self):
        return self

    def one_or_none(self):
        return {"id": 99, "metadata_json": {"x": 1}, "status": "parsed", "round_label": "JORNADA6"}


class _Session:
    def __init__(self):
        self.calls = []

    def execute(self, query, params):
        self.calls.append((str(query), params))
        if len(self.calls) == 1:
            return _ResultExisting()

        class _R:
            def one(self):
                return [99, False]

        return _R()


def test_existing_parsed_target_preserves_status_and_round_label():
    s = _Session()
    repo = PostgresTargetRepository(s)
    out = repo.upsert_target(
        source_name="besoccer",
        target_type="match_page",
        url="https://es.besoccer.com/partido/a/b/2026239018",
        source_match_id="2026239018",
        payload={
            "source_competition_slug": "clausura_mexico",
            "season_key": "clausura-2026",
            "round_label": "JORNADA1",
            "status": "pending",
            "metadata_json": {"last_seen_at": "2026-05-15T00:00:00+00:00"},
        },
    )
    assert out["updated"] is False
    assert out["updated_safe"] is True
    assert out["skipped_existing"] is True
    assert len(s.calls) == 2
    update_sql, _ = s.calls[1]
    assert "SET metadata_json" in update_sql
    assert "status =" not in update_sql
    assert "round_label =" not in update_sql

