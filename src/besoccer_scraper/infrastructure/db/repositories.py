from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
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
                    st.url
                FROM scrape_targets st
                WHERE
                    st.source_competition_slug = :competition
                    AND st.season_key = :season_key
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
                        m.source_competition_slug = :competition
                        AND m.season_key = :season_key
                ) AS matches_total,
                (
                    SELECT COUNT(*)::BIGINT
                    FROM raw_pages rp
                    WHERE rp.url IN (
                        SELECT tb.url
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


class PostgresTargetRepository(ScrapeTargetsRepository):
    def upsert_target(self, *, source_name: str, target_type: str, url: str, source_match_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        query = text(
            """
            INSERT INTO scrape_targets (source_name, target_type, url, source_match_id, source_competition_slug, season_key, round_label, status, metadata_json)
            VALUES (:source_name, :target_type, :url, :source_match_id, :source_competition_slug, :season_key, :round_label, :status, :metadata_json)
            ON CONFLICT (source_name, target_type, url)
            DO UPDATE SET
                source_match_id = EXCLUDED.source_match_id,
                source_competition_slug = EXCLUDED.source_competition_slug,
                season_key = EXCLUDED.season_key,
                round_label = EXCLUDED.round_label,
                status = EXCLUDED.status,
                metadata_json = EXCLUDED.metadata_json,
                updated_at = NOW()
            RETURNING id, (xmax = 0) AS inserted
            """
        ).bindparams(bindparam("metadata_json", type_=JSONB))
        row = self.session.execute(
            query,
            {
                "source_name": source_name,
                "target_type": target_type,
                "url": url,
                "source_match_id": source_match_id,
                "source_competition_slug": payload.get("source_competition_slug") or payload.get("competition"),
                "season_key": payload.get("season_key"),
                "round_label": payload.get("round_label"),
                "status": payload.get("status", "pending"),
                "metadata_json": payload.get("metadata_json") or payload,
            },
        ).one()
        return {"id": int(row[0]), "inserted": bool(row[1]), "updated": not bool(row[1])}

    def list_recent_by_competition_season(self, *, competition: str, season_key: str, limit: int = 10) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT id, source_match_id, round_label, status, url
            FROM scrape_targets
            WHERE source_name = 'besoccer'
              AND source_competition_slug = :competition
              AND season_key = :season_key
            ORDER BY id DESC
            LIMIT :limit
            """
        )
        return list(self.session.execute(query, {"competition": competition, "season_key": season_key, "limit": limit}).mappings())

    def list_for_processing(self, *, limit: int) -> list[dict[str, Any]]:
        query = text(
            """
            SELECT
                id,
                source_name,
                target_type,
                url,
                source_match_id,
                metadata_json,
                source_competition_slug AS competition_slug,
                round_label,
                season_key
            FROM scrape_targets
            WHERE status IN ('pending', 'discovered', 'retry_scheduled')
            ORDER BY id
            LIMIT :limit
            """
        )
        return list(self.session.execute(query, {"limit": limit}).mappings())

    def list_pending(self, *, limit: int) -> list[dict[str, Any]]:
        return self.list_for_processing(limit=limit)

    def mark_in_progress(self, *, target_id: int) -> None:
        self._set_status(target_id=target_id, status="in_progress")

    def mark_scraped(self, *, target_id: int) -> None:
        self._set_status(target_id=target_id, status="scraped")

    def mark_parsed(self, *, target_id: int) -> None:
        self._set_status(target_id=target_id, status="parsed")

    def mark_failed(self, *, target_id: int, error: str) -> None:
        self._set_status(target_id=target_id, status="failed", error=error)

    def mark_transition(
        self,
        *,
        target_id: int,
        from_statuses: tuple[str, ...],
        to_status: str,
        error: str | None = None,
    ) -> bool:
        query = text(
            """
            UPDATE scrape_targets
            SET status = :to_status, last_error = :error, updated_at = NOW()
            WHERE id = :target_id
              AND status = ANY(:from_statuses)
            """
        )
        result = self.session.execute(
            query,
            {"target_id": target_id, "to_status": to_status, "error": error, "from_statuses": list(from_statuses)},
        )
        return result.rowcount > 0

    def count_by_status(self) -> dict[str, int]:
        query = text(
            """
            SELECT status, COUNT(*)::BIGINT AS total
            FROM scrape_targets
            GROUP BY status
            """
        )
        return {str(row["status"]): int(row["total"]) for row in self.session.execute(query).mappings()}

    def count_by_competition_season(self, *, competition: str, season_key: str) -> int:
        query = text(
            """
            SELECT COUNT(*)::BIGINT AS total
            FROM scrape_targets
            WHERE source_competition_slug = :competition
              AND season_key = :season_key
            """
        )
        row = self.session.execute(query, {"competition": competition, "season_key": season_key}).one()
        return int(row[0])

    def _set_status(self, *, target_id: int, status: str, error: str | None = None) -> None:
        self.mark_transition(
            target_id=target_id,
            from_statuses=("pending", "discovered", "in_progress", "retry_scheduled", "parsed", "blocked", "failed_permanent"),
            to_status=status,
            error=error,
        )


class PostgresRawPageRepository(RawPagesRepository):
    def save_raw_page(
        self,
        *,
        source_name: str,
        url: str,
        content_hash: str,
        body: str,
        status_code: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        query = text(
            """
            INSERT INTO raw_pages (source_name, url, body_hash, body, status_code)
            VALUES (:source_name, :url, :content_hash, :body, :status_code)
            ON CONFLICT DO NOTHING
            RETURNING id
            """
        )
        row = self.session.execute(
            query,
            {"source_name": source_name, "url": url, "content_hash": content_hash, "body": body, "status_code": status_code},
        ).one_or_none()
        if row is not None:
            return int(row[0])
        existing = self.session.execute(
            text(
                """
                SELECT id
                FROM raw_pages
                WHERE source_name = :source_name AND url = :url AND body_hash = :content_hash
                LIMIT 1
                """
            ),
            {"source_name": source_name, "url": url, "content_hash": content_hash},
        ).one()
        return int(existing[0])


class PostgresMatchRepository(MatchesRepository):
    def upsert_match(self, *, source_id: int, source_match_id: str, payload: dict[str, Any], season_id: int | None = None) -> int:
        query = text(
            """
            INSERT INTO matches (source_id, source_match_id, season_id, payload)
            VALUES (:source_id, :source_match_id, :season_id, :payload)
            ON CONFLICT (source_id, source_match_id)
            DO UPDATE SET season_id = EXCLUDED.season_id, payload = EXCLUDED.payload
            RETURNING id
            """
        ).bindparams(bindparam("metadata_json", type_=JSONB))
        row = self.session.execute(
            query,
            {"source_id": source_id, "source_match_id": source_match_id, "season_id": season_id, "payload": payload},
        ).one()
        return int(row[0])

    def get_by_source_match_id(self, *, source_id: int, source_match_id: str) -> dict[str, Any] | None:
        row = self.session.execute(
            text("SELECT * FROM matches WHERE source_id = :source_id AND source_match_id = :source_match_id"),
            {"source_id": source_id, "source_match_id": source_match_id},
        ).mappings().one_or_none()
        return dict(row) if row else None

    def count_by_competition_season(self, *, competition: str, season_key: str) -> int:
        row = self.session.execute(
            text(
                """
                SELECT COUNT(*)::BIGINT AS total
                FROM matches
                WHERE COALESCE(payload ->> 'competition', payload ->> 'competition_slug', payload ->> 'competition_id') = :competition
                  AND COALESCE(payload ->> 'season_key', payload ->> 'season') = :season_key
                """
            ),
            {"competition": competition, "season_key": season_key},
        ).one()
        return int(row[0])


class PostgresRunRepository(JobRunsRepository):
    def start_run(self, *, job_name: str, metadata: dict[str, Any] | None = None) -> int:
        return self.start(job_name)

    def finish_run(self, *, run_id: int, status: str, stats: dict[str, Any] | None = None) -> None:
        self.finish(run_id=run_id, status=status)

    def log_event(self, *, run_id: int, event_type: str, payload: dict[str, Any]) -> None:
        message = f"{event_type}: {payload}"
        self.session.execute(
            text(
                """
                INSERT INTO job_logs (job_run_id, log_level, message)
                VALUES (:run_id, 'INFO', :message)
                """
            ),
            {"run_id": run_id, "message": message},
        )


@dataclass
class PostgresUnitOfWork:
    session: Session

    def __post_init__(self) -> None:
        self.sources = SourcesRepository(self.session)
        self.competitions = CompetitionsRepository(self.session)
        self.seasons = SeasonsRepository(self.session)
        self.teams = TeamsRepository(self.session)
        self.scrape_targets = PostgresTargetRepository(self.session)
        self.raw_pages = PostgresRawPageRepository(self.session)
        self.matches = PostgresMatchRepository(self.session)
        self.job_runs = PostgresRunRepository(self.session)
        self.job_logs = JobLogsRepository(self.session)
        self.run_locks = RunLocksRepository(self.session)

    def commit(self) -> None:
        self.session.commit()
