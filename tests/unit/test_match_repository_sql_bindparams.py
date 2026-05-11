import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from besoccer_scraper.infrastructure.db.repositories import PostgresMatchRepository


class Session:
    def execute(self, query, params):
        sql = str(query)
        assert ":metadata_json" not in sql
        assert "stats_json" in sql
        class R:
            def one(self): return [1]
        return R()


def test_upsert_match_no_metadata_bindparam():
    repo = PostgresMatchRepository(Session())
    out = repo.upsert_match(source_id=1, source_match_id="2026239018", payload={"stats_json": {}, "events_json": []})
    assert out == 1
