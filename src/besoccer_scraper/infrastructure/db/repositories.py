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

    def coverage_by_competition_season(self, *, competition: str, season_key: str) -> dict[str, int | float | str | None]:
        query = text(
            """
            WITH target_base AS (
                SELECT
                    st.source_match_id,
                    st.status,
                    st.payload
                FROM scrape_targets st
                WHERE
                    COALESCE(st.payload ->> 'competition', st.payload ->> 'competition_slug', st.payload ->> 'competition_id') = :competition
                    AND COALESCE(st.payload ->> 'season_key', st.payload ->> 'season') = :season_key
            ),
            duplicates AS (
                SELECT COUNT(*)::BIGINT AS duplicates_detected
                FROM (
                    SELECT source_match_id
                    FROM target_base
                    WHERE source_match_id IS NOT NULL
                    GROUP BY source_match_id
                    HAVING COUNT(*) > 1
                ) d
            )
            SELECT
                COUNT(*)::BIGINT AS targets_total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END)::BIGINT AS pending,
                SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END)::BIGINT AS in_progress,
                SUM(CASE WHEN status = 'parsed' THEN 1 ELSE 0 END)::BIGINT AS parsed,
                SUM(CASE WHEN status = 'retry_scheduled' THEN 1 ELSE 0 END)::BIGINT AS retry_scheduled,
                SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END)::BIGINT AS blocked,
                SUM(CASE WHEN status = 'failed_permanent' THEN 1 ELSE 0 END)::BIGINT AS failed_permanent,
                (
                    SELECT COUNT(*)::BIGINT
                    FROM matches m
                    WHERE
                        COALESCE(m.payload ->> 'competition', m.payload ->> 'competition_slug', m.competition_id) = :competition
                        AND COALESCE(m.payload ->> 'season_key', m.payload ->> 'season') = :season_key
                ) AS matches_total,
                (
                    SELECT COUNT(*)::BIGINT
                    FROM raw_pages rp
                    WHERE rp.url IN (
                        SELECT COALESCE(tb.payload ->> 'url', tb.payload ->> 'source_url')
                        FROM target_base tb
                    )
                ) AS raw_pages_total,
                (SELECT duplicates_detected FROM duplicates) AS duplicates_detected,
                CASE
                    WHEN COUNT(*) = 0 THEN 0.0
                    ELSE ROUND((SUM(CASE WHEN status = 'parsed' THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric), 4)
                END AS coverage_estimated
            FROM target_base;
            """
        )
        row = self.session.execute(query, {"competition": competition, "season_key": season_key}).mappings().one()
        return dict(row)


class RawPagesRepository(BaseRepository):
    table_name = "raw_pages"


class MatchesRepository(BaseRepository):
    table_name = "matches"


class JobRunsRepository(BaseRepository):
    table_name = "job_runs"

    def start(self, job_name: str) -> int:
        row = self.session.execute(
            text(
                """
                INSERT INTO job_runs (job_name, status)
                VALUES (:job_name, 'running')
                RETURNING id
                """
            ),
            {"job_name": job_name},
        ).one()
        return int(row[0])

    def finish(self, *, run_id: int, status: str) -> None:
        self.session.execute(
            text(
                """
                UPDATE job_runs
                SET status = :status, finished_at = NOW()
                WHERE id = :run_id
                """
            ),
            {"status": status, "run_id": run_id},
        )


class JobLogsRepository(BaseRepository):
    table_name = "job_logs"

    def append(self, *, job_run_id: int, log_level: str, message: str) -> None:
        self.insert(job_run_id=job_run_id, log_level=log_level, message=message)


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
