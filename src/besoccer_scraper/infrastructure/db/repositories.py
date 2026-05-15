from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from besoccer_scraper.domain.entities import Match


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
        if source_match_id:
            existing = self.session.execute(
                text(
                    """
                    SELECT id, metadata_json
                    FROM scrape_targets
                    WHERE source_name = :source_name
                      AND target_type = :target_type
                      AND source_match_id = :source_match_id
                    LIMIT 1
                    """
                ),
                {"source_name": source_name, "target_type": target_type, "source_match_id": source_match_id},
            ).mappings().one_or_none()
            if existing is not None:
                existing_meta = dict(existing.get("metadata_json") or {})
                incoming_meta = payload.get("metadata_json") or {}
                existing_meta.update(
                    {
                        "last_seen_at": incoming_meta.get("last_seen_at"),
                        "discovery_last_seen_at": incoming_meta.get("discovery_last_seen_at"),
                        "last_discovery_strategy": incoming_meta.get("last_discovery_strategy") or incoming_meta.get("discovery_strategy"),
                    }
                )
                metadata_json = {k: v for k, v in existing_meta.items() if v is not None}
                self.session.execute(
                    text(
                        """
                        UPDATE scrape_targets
                        SET metadata_json = :metadata_json, updated_at = NOW()
                        WHERE id = :id
                        """
                    ).bindparams(bindparam("metadata_json", type_=JSONB)),
                    {"id": int(existing["id"]), "metadata_json": metadata_json},
                )
                return {"id": int(existing["id"]), "inserted": False, "updated": False, "updated_safe": True, "skipped_existing": True}
        query = text(
            """
            INSERT INTO scrape_targets (source_name, target_type, url, source_match_id, source_competition_slug, season_key, round_label, status, metadata_json)
            VALUES (:source_name, :target_type, :url, :source_match_id, :source_competition_slug, :season_key, :round_label, :status, :metadata_json)
            ON CONFLICT (source_name, target_type, url)
            DO UPDATE SET
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
        inserted = bool(row[1])
        return {
            "id": int(row[0]),
            "inserted": inserted,
            "updated": False,
            "updated_safe": (not inserted),
            "skipped_existing": (not inserted),
        }

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
    def ensure_source(self, name: str = "besoccer") -> int:
        row = self.session.execute(
            text(
                """
                INSERT INTO sources (source_name)
                VALUES (:name)
                ON CONFLICT (source_name) DO UPDATE SET source_name = EXCLUDED.source_name
                RETURNING id
                """
            ),
            {"name": name},
        ).one_or_none()
        if row is not None:
            return int(row[0])
        existing = self.session.execute(text("SELECT id FROM sources WHERE source_name = :name LIMIT 1"), {"name": name}).one()
        return int(existing[0])

    def upsert_many(self, matches: list[Match]) -> int:
        count = 0
        source_id = self.ensure_source("besoccer")
        for match in matches:
            payload = dict(match.payload or {})
            source_id_item = int(payload.get("source_id") or source_id)
            self.upsert_match(source_id=source_id_item, source_match_id=str(match.external_id), payload=payload, season_id=None)
            count += 1
        return count

    def upsert_match(self, *, source_id: int, source_match_id: str, payload: dict[str, Any], season_id: int | None = None) -> int:
        metadata = payload.get("metadata") or {}
        score = str(metadata.get("score") or "")
        home_score = payload.get("home_score")
        away_score = payload.get("away_score")
        if (home_score is None or away_score is None) and "-" in score:
            parts = [p.strip() for p in score.split("-", 1)]
            if len(parts) == 2 and all(p.isdigit() for p in parts):
                home_score, away_score = int(parts[0]), int(parts[1])

        query = text(
            """
            INSERT INTO matches (
                source_id, source_name, source_match_id, season_id, payload, url, source_competition_slug,
                competition_name, season_key, round_label, match_date_utc, status, home_team_name,
                away_team_name, home_score, away_score, venue, stats_json, events_json, raw_page_id
            )
            VALUES (
                :source_id, :source_name, :source_match_id, :season_id, :payload, :url, :source_competition_slug,
                :competition_name, :season_key, :round_label, :match_date_utc, :status, :home_team_name,
                :away_team_name, :home_score, :away_score, :venue, :stats_json, :events_json, :raw_page_id
            )
            ON CONFLICT (source_name, source_match_id)
            DO UPDATE SET
                payload = EXCLUDED.payload,
                url = EXCLUDED.url,
                source_competition_slug = EXCLUDED.source_competition_slug,
                competition_name = EXCLUDED.competition_name,
                season_key = EXCLUDED.season_key,
                round_label = EXCLUDED.round_label,
                match_date_utc = EXCLUDED.match_date_utc,
                status = EXCLUDED.status,
                home_team_name = EXCLUDED.home_team_name,
                away_team_name = EXCLUDED.away_team_name,
                home_score = EXCLUDED.home_score,
                away_score = EXCLUDED.away_score,
                venue = EXCLUDED.venue,
                stats_json = EXCLUDED.stats_json,
                events_json = EXCLUDED.events_json,
                raw_page_id = EXCLUDED.raw_page_id,
                updated_at = NOW()
            RETURNING id
            """
        ).bindparams(bindparam("payload", type_=JSONB), bindparam("stats_json", type_=JSONB), bindparam("events_json", type_=JSONB))
        row = self.session.execute(
            query,
            {
                "source_id": source_id,
                "source_name": payload.get("source_name") or "besoccer",
                "source_match_id": source_match_id,
                "season_id": season_id,
                "payload": payload,
                "url": payload.get("url") or metadata.get("canonical_url"),
                "source_competition_slug": payload.get("source_competition_slug") or payload.get("competition_slug"),
                "competition_name": payload.get("competition_name") or metadata.get("competition_name"),
                "season_key": payload.get("season_key"),
                "round_label": payload.get("round_label"),
                "match_date_utc": payload.get("match_date_utc") or metadata.get("date_utc"),
                "status": payload.get("status") or metadata.get("status"),
                "home_team_name": payload.get("home_team_name") or metadata.get("home_team_name") or payload.get("home_team"),
                "away_team_name": payload.get("away_team_name") or metadata.get("away_team_name") or payload.get("away_team"),
                "home_score": home_score,
                "away_score": away_score,
                "venue": payload.get("venue") or metadata.get("venue"),
                "stats_json": payload.get("stats_json") or {},
                "events_json": payload.get("events_json") or [],
                "raw_page_id": payload.get("raw_page_id"),
            },
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

    def list_matches_for_rescrape(
        self,
        *,
        competition_slug: str,
        season_key: str,
        limit: int | None = None,
        source_match_id: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT
                id,
                source_match_id,
                url,
                source_competition_slug,
                season_key,
                round_label
            FROM matches
            WHERE source_competition_slug = :competition_slug
              AND season_key = :season_key
        """
        params: dict[str, Any] = {"competition_slug": competition_slug, "season_key": season_key}
        if source_match_id is not None:
            sql += " AND source_match_id = :source_match_id"
            params["source_match_id"] = str(source_match_id)
        sql += " ORDER BY id"
        if limit is not None:
            sql += " LIMIT :limit"
            params["limit"] = int(limit)
        return list(self.session.execute(text(sql), params).mappings())


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
