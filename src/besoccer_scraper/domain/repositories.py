from __future__ import annotations

from typing import Protocol, Iterable

from .entities import Competition, Match, AuditEvent


class CompetitionRepository(Protocol):
    def upsert_many(self, competitions: Iterable[Competition]) -> int: ...


class MatchRepository(Protocol):
    def upsert_many(self, matches: Iterable[Match]) -> int: ...


class AuditRepository(Protocol):
    def append(self, event: AuditEvent) -> None: ...


class UnitOfWork(Protocol):
    competitions: CompetitionRepository
    matches: MatchRepository
    audits: AuditRepository

    def commit(self) -> None: ...
