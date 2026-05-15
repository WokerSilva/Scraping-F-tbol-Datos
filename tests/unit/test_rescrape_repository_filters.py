import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from besoccer_scraper.infrastructure.db.repositories import PostgresMatchRepository


class _Result:
    def mappings(self):
        return self

    def __iter__(self):
        return iter([{"id": 1}])


class _Session:
    def __init__(self):
        self.sql = ""
        self.params = {}

    def execute(self, query, params):
        self.sql = str(query)
        self.params = params
        return _Result()


def test_rescrape_lists_existing_matches():
    session = _Session()
    repo = PostgresMatchRepository(session)
    out = repo.list_matches_for_rescrape(competition_slug="clausura_mexico", season_key="clausura-2026", limit=10)
    assert out == [{"id": 1}]
    assert "source_competition_slug = :competition_slug" in session.sql
    assert "season_key = :season_key" in session.sql
    assert session.params["competition_slug"] == "clausura_mexico"
    assert session.params["season_key"] == "clausura-2026"
    assert session.params["limit"] == 10
