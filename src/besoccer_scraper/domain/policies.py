from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from besoccer_scraper.domain.enums import TargetStatus


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int

    def should_retry(self, retries: int) -> bool:
        return retries < self.max_retries

    def next_retry_at(self, retries: int, *, now: datetime | None = None, base_seconds: int = 60) -> datetime:
        current = now or datetime.now(timezone.utc)
        delay = base_seconds * (2**max(retries, 0))
        return current + timedelta(seconds=delay)


@dataclass(frozen=True)
class TargetSelectionPolicy:
    limit: int = 50
    allowed_statuses: tuple[TargetStatus, ...] = (TargetStatus.PENDING, TargetStatus.RETRY_SCHEDULED)

    def matches_status(self, status: str) -> bool:
        return status in {item.value for item in self.allowed_statuses}


@dataclass(frozen=True)
class RunLockPolicy:
    lock_name: str = "scrape:pending_matches"
    ttl_seconds: int = 900

    def expires_at(self, *, now: datetime | None = None) -> datetime:
        current = now or datetime.now(timezone.utc)
        return current + timedelta(seconds=self.ttl_seconds)


@dataclass(frozen=True)
class ThrottlingPolicy:
    min_interval_seconds: float = 0.0

    def sleep_seconds(self, elapsed_seconds: float) -> float:
        return max(0.0, self.min_interval_seconds - max(0.0, elapsed_seconds))


@dataclass(frozen=True)
class RequestPolicy:
    timeout_seconds: float
    user_agent: str
