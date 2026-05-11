import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from besoccer_scraper.infrastructure.db.repositories import PostgresMatchRepository


class Session:
    def __init__(self): self.calls = 0
    def execute(self, query, params):
        self.calls += 1
        class R:
            def __init__(self, calls): self.calls = calls
            def one_or_none(self): return [7]
            def one(self): return [7]
        return R(self.calls)


def test_ensure_source_returns_real_id():
    repo = PostgresMatchRepository(Session())
    assert repo.ensure_source("besoccer") == 7
