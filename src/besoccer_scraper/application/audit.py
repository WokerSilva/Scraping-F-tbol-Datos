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
