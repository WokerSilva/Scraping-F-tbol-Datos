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
    uow: object

    def execute(self, *, competition: str, season_key: str) -> dict[str, int | float | str | None]:
        run_id: int | None = None
        if hasattr(self.uow, "job_runs") and hasattr(self.uow.job_runs, "start"):
            run_id = self.uow.job_runs.start("audit.coverage")

        try:
            coverage = self.uow.scrape_targets.coverage_by_competition_season(
                competition=competition,
                season_key=season_key,
            )
            if run_id is not None and hasattr(self.uow, "job_logs") and hasattr(self.uow.job_logs, "append"):
                self.uow.job_logs.append(
                    job_run_id=run_id,
                    log_level="INFO",
                    message=(
                        "audit.coverage computed "
                        f"competition={competition} season_key={season_key} "
                        f"targets_total={coverage.get('targets_total', 0)} parsed={coverage.get('parsed', 0)}"
                    ),
                )
            if run_id is not None and hasattr(self.uow.job_runs, "finish"):
                self.uow.job_runs.finish(run_id=run_id, status="success")
            self.uow.commit()
            return coverage
        except Exception as exc:
            if run_id is not None and hasattr(self.uow, "job_logs") and hasattr(self.uow.job_logs, "append"):
                self.uow.job_logs.append(
                    job_run_id=run_id,
                    log_level="ERROR",
                    message=(
                        "audit.coverage failed "
                        f"competition={competition} season_key={season_key} error={exc}"
                    ),
                )
            if run_id is not None and hasattr(self.uow.job_runs, "finish"):
                self.uow.job_runs.finish(run_id=run_id, status="failed")
            self.uow.commit()
            raise
