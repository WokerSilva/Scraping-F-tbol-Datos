from __future__ import annotations

from collections.abc import Iterable

from besoccer_scraper.domain.entities import Competition, Match, AuditEvent
from besoccer_scraper.domain.repositories import UnitOfWork


class InMemoryCompetitionRepository:
    def __init__(self) -> None:
        self.items: dict[str, Competition] = {}

    def upsert_many(self, competitions: Iterable[Competition]) -> int:
        count = 0
        for c in competitions:
            self.items[c.external_id] = c
            count += 1
        return count


class InMemoryMatchRepository:
    def __init__(self) -> None:
        self.items: dict[str, Match] = {}

    def upsert_many(self, matches: Iterable[Match]) -> int:
        count = 0
        for m in matches:
            self.items[m.external_id] = m
            count += 1
        return count


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self.events.append(event)


class PostgresUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.competitions = InMemoryCompetitionRepository()
        self.matches = InMemoryMatchRepository()
        self.audits = InMemoryAuditRepository()

    def commit(self) -> None:
        return None
