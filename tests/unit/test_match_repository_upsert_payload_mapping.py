import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from besoccer_scraper.infrastructure.db.repositories import PostgresMatchRepository


class Session:
    def execute(self, query, params):
        assert params["source_match_id"] == "2026239018"
        assert params["home_team_name"] == "Mazatlán"
        assert params["away_team_name"] == "FC Juárez"
        assert params["home_score"] == 1
        assert params["away_score"] == 2
        class R:
            def one(self): return [77]
        return R()


def test_upsert_payload_mapping():
    repo = PostgresMatchRepository(Session())
    payload = {
        "home_team_name": "Mazatlán", "away_team_name": "FC Juárez", "round_label": "JORNADA1",
        "competition_name": "Liga MX - Clausura", "stats_json": {}, "events_json": [], "metadata": {"score": "1-2"}
    }
    assert repo.upsert_match(source_id=1, source_match_id="2026239018", payload=payload) == 77
