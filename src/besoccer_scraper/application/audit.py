from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

from besoccer_scraper.domain.entities import AuditEvent
from besoccer_scraper.domain.repositories import UnitOfWork


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
