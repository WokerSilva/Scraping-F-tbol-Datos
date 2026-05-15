from __future__ import annotations

from typing import Protocol, Iterable

from .entities import Competition, Match, AuditEvent


class CompetitionRepository(Protocol):
    def upsert_many(self, competitions: Iterable[Competition]) -> int: ...


class MatchRepository(Protocol):
    def upsert_many(self, matches: Iterable[Match]) -> int: ...
    def list_matches_for_rescrape(
        self,
        *,
        competition_slug: str,
        season_key: str,
        limit: int | None = None,
        source_match_id: str | None = None,
    ) -> list[dict]: ...


class AuditRepository(Protocol):
    def append(self, event: AuditEvent) -> None: ...


class UnitOfWork(Protocol):
    competitions: CompetitionRepository
    matches: MatchRepository
    audits: AuditRepository
    scrape_targets: "TargetRepository"
    raw_pages: "RawPageRepository"
    job_runs: "RunRepository"

    def commit(self) -> None: ...


class TargetRepository(Protocol):
    def upsert_target(self, *, source_name: str, target_type: str, url: str, source_match_id: str | None, payload: dict) -> int: ...
    def list_pending(self, *, limit: int) -> list[dict]: ...
    def mark_in_progress(self, *, target_id: int) -> None: ...
    def mark_scraped(self, *, target_id: int) -> None: ...
    def mark_parsed(self, *, target_id: int) -> None: ...
    def mark_failed(self, *, target_id: int, error: str) -> None: ...
    def count_by_status(self) -> dict[str, int]: ...
    def count_by_competition_season(self, *, competition: str, season_key: str) -> int: ...


class DiscoverySeasonTargetRepository(Protocol):
    def upsert_target(self, *, source_name: str, target_type: str, url: str, source_match_id: str | None, payload: dict) -> int: ...


class ScrapeMatchTargetRepository(Protocol):
    def mark_transition(self, *, target_id: int, from_statuses: tuple[str, ...], to_status: str, error: str | None = None) -> bool: ...


class PendingBatchTargetRepository(Protocol):
    def list_for_processing(self, *, limit: int) -> list[dict]: ...


class RawPageRepository(Protocol):
    def save_raw_page(
        self,
        *,
        source_name: str,
        url: str,
        content_hash: str,
        body: str,
        status_code: int | None,
        metadata: dict | None = None,
    ) -> int: ...


class RunRepository(Protocol):
    def start_run(self, *, job_name: str, metadata: dict | None = None) -> int: ...
    def finish_run(self, *, run_id: int, status: str, stats: dict | None = None) -> None: ...
    def log_event(self, *, run_id: int, event_type: str, payload: dict) -> None: ...
