from __future__ import annotations

from dataclasses import dataclass

from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import UnitOfWork


@dataclass
class DiscoverCompetitionsUseCase:
    uow: UnitOfWork
    http_client: object
    parser: object
    request_policy: RequestPolicy

    def execute(self, source_url: str) -> int:
        html = self.http_client.get(source_url)
        competitions = self.parser.parse(html)
        count = self.uow.competitions.upsert_many(competitions)
        self.uow.commit()
        return count
