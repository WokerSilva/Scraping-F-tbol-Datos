from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class BaseRepository:
    table_name: str

    def __init__(self, session: Session) -> None:
        self.session = session

    def insert(self, **values: Any) -> None:
        columns = ", ".join(values.keys())
        params = ", ".join(f":{k}" for k in values.keys())
        self.session.execute(text(f"INSERT INTO {self.table_name} ({columns}) VALUES ({params})"), values)


class SourcesRepository(BaseRepository):
    table_name = "sources"


class CompetitionsRepository(BaseRepository):
    table_name = "competitions"


class SeasonsRepository(BaseRepository):
    table_name = "seasons"


class TeamsRepository(BaseRepository):
    table_name = "teams"


class ScrapeTargetsRepository(BaseRepository):
    table_name = "scrape_targets"


class RawPagesRepository(BaseRepository):
    table_name = "raw_pages"


class MatchesRepository(BaseRepository):
    table_name = "matches"


class JobRunsRepository(BaseRepository):
    table_name = "job_runs"


class JobLogsRepository(BaseRepository):
    table_name = "job_logs"


class RunLocksRepository(BaseRepository):
    table_name = "run_locks"


@dataclass
class PostgresUnitOfWork:
    session: Session

    def __post_init__(self) -> None:
        self.sources = SourcesRepository(self.session)
        self.competitions = CompetitionsRepository(self.session)
        self.seasons = SeasonsRepository(self.session)
        self.teams = TeamsRepository(self.session)
        self.scrape_targets = ScrapeTargetsRepository(self.session)
        self.raw_pages = RawPagesRepository(self.session)
        self.matches = MatchesRepository(self.session)
        self.job_runs = JobRunsRepository(self.session)
        self.job_logs = JobLogsRepository(self.session)
        self.run_locks = RunLocksRepository(self.session)

    def commit(self) -> None:
        self.session.commit()
