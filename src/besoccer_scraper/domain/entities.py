from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Competition:
    external_id: str
    name: str
    country: str | None = None


@dataclass(frozen=True)
class Match:
    external_id: str
    competition_id: str
    home_team: str
    away_team: str
    kickoff_at: datetime | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEvent:
    run_id: str
    message: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
