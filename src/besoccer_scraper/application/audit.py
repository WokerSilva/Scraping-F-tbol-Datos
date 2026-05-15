from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid
from typing import Any

from sqlalchemy import text

from besoccer_scraper.domain.entities import AuditEvent
from besoccer_scraper.domain.repositories import UnitOfWork
from besoccer_scraper.domain.services import build_season_key


@dataclass
class AuditRunUseCase:
    uow: UnitOfWork

    def execute(self, message: str) -> str:
        run_id = str(uuid.uuid4())
        self.uow.audits.append(
            AuditEvent(run_id=run_id, message=message, created_at=datetime.now(timezone.utc))
        )
        self.uow.commit()
        return run_id


@dataclass
class AuditCoverageUseCase:
    uow: UnitOfWork

    def execute(self, *, competition: str, season_key: str) -> dict[str, int | float | str | None]:
        run_id: int | None = None
        run_id = self.uow.job_runs.start_run(job_name="audit.coverage")

        try:
            coverage = self.uow.scrape_targets.coverage_by_competition_season(
                competition=competition,
                season_key=season_key,
            )
            self.uow.job_runs.log_event(
                run_id=run_id,
                event_type="coverage.computed",
                payload={
                    "competition": competition,
                    "season_key": season_key,
                    "targets_total": coverage.get("targets_total", 0),
                    "parsed": coverage.get("parsed", 0),
                },
            )
            self.uow.job_runs.finish_run(run_id=run_id, status="success")
            self.uow.commit()
            return coverage
        except Exception as exc:
            self.uow.job_runs.log_event(
                run_id=run_id,
                event_type="coverage.failed",
                payload={"competition": competition, "season_key": season_key, "error": str(exc)},
            )
            self.uow.job_runs.finish_run(run_id=run_id, status="failed")
            self.uow.commit()
            raise


@dataclass
class AuditMxSeasonUseCase:
    uow: UnitOfWork

    def execute(self, *, competition: str, year: int) -> dict[str, Any]:
        season_key = build_season_key(competition, year)
        coverage = self.uow.scrape_targets.coverage_by_competition_season(competition=competition, season_key=season_key)

        rows = self.uow.session.execute(
            text(
                """
                SELECT COALESCE(st.round_label, 'unknown') AS round_label, COUNT(*)::BIGINT AS total
                FROM scrape_targets st
                WHERE st.source_competition_slug = :competition
                  AND st.season_key = :season_key
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"competition": competition, "season_key": season_key},
        ).mappings()

        rounds = {str(row["round_label"]): int(row["total"]) for row in rows}
        expected_rounds = 17
        expected_matches = 153
        matches_total = int(coverage.get("matches_total", 0) or 0)

        return {
            "competition": competition,
            "season_key": season_key,
            "targets_total": int(coverage.get("targets_total", 0) or 0),
            "status_breakdown": {
                key: int(coverage.get(key, 0) or 0)
                for key in ("pending", "in_progress", "parsed", "retry_scheduled", "blocked", "failed_permanent")
            },
            "matches_total": matches_total,
            "rounds_detected": len(rounds),
            "round_label_counts": rounds,
            "duplicates_avoided": int(coverage.get("duplicates_detected", 0) or 0),
            "expected_rounds": expected_rounds,
            "expected_matches": expected_matches,
            "gap_rounds": expected_rounds - len(rounds),
            "gap_matches": expected_matches - matches_total,
        }


@dataclass
class InspectMatchUseCase:
    uow: UnitOfWork

    def execute(self, *, source_match_id: str) -> dict[str, Any] | None:
        row = self.uow.session.execute(
            text("SELECT payload FROM matches WHERE source_match_id = :source_match_id ORDER BY id DESC LIMIT 1"),
            {"source_match_id": source_match_id},
        ).mappings().one_or_none()
        if row is None:
            return None

        payload = dict(row).get("payload") or {}
        metadata = payload.get("metadata") or {}
        stats = payload.get("stats_json") or {}
        events = payload.get("events_json") or []

        goals = [
            {
                "minute": event.get("minute"),
                "minute_raw": event.get("minute_raw"),
                "half": event.get("half"),
                "player_name": event.get("player_name"),
                "team_side": event.get("team_side"),
            }
            for event in events
            if isinstance(event, dict) and event.get("event_type") == "goal"
        ]

        return {
            "source_match_id": payload.get("source_match_id") or source_match_id,
            "url": payload.get("url"),
            "competition_slug": payload.get("competition_slug"),
            "season_key": payload.get("season_key"),
            "round_label": payload.get("round_label"),
            "home_team": metadata.get("home_team") or metadata.get("home_team_name") or payload.get("home_team") or payload.get("home_team_name"),
            "away_team": metadata.get("away_team") or metadata.get("away_team_name") or payload.get("away_team") or payload.get("away_team_name"),
            "score": metadata.get("score") or payload.get("score"),
            "venue": metadata.get("venue") or payload.get("venue"),
            "status": metadata.get("status") or payload.get("status"),
            "stats_count": len(stats),
            "goals_count": len(goals),
            "metadata": metadata,
            "stats_summary": {"total_metrics": len(stats), "keys": sorted(stats.keys())[:10]},
            "goals": goals,
        }


@dataclass
class InspectTargetsUseCase:
    uow: UnitOfWork

    def execute(self, *, competition: str, year: int) -> dict[str, Any]:
        season_key = build_season_key(competition, year)
        coverage = self.uow.scrape_targets.coverage_by_competition_season(competition=competition, season_key=season_key)
        round_rows = self.uow.session.execute(
            text("""
                SELECT COALESCE(round_label, 'unknown') AS round_label, COUNT(*)::BIGINT AS total
                FROM scrape_targets
                WHERE source_name = 'besoccer' AND source_competition_slug = :competition AND season_key = :season_key
                GROUP BY 1 ORDER BY 1
            """),
            {"competition": competition, "season_key": season_key},
        ).mappings()
        recent = self.uow.scrape_targets.list_recent_by_competition_season(competition=competition, season_key=season_key, limit=10)
        return {
            "competition": competition,
            "season_key": season_key,
            "targets_total": int(coverage.get("targets_total", 0) or 0),
            "status_breakdown": {k: int(coverage.get(k, 0) or 0) for k in ("pending", "in_progress", "parsed", "retry_scheduled", "blocked", "failed_permanent")},
            "round_label_counts": {str(r["round_label"]): int(r["total"]) for r in round_rows},
            "recent": [dict(r) for r in recent],
        }
