from __future__ import annotations

from dataclasses import dataclass

from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import UnitOfWork


@dataclass
class ScrapeMatchesUseCase:
    uow: UnitOfWork
    http_client: object
    parser: object
    request_policy: RequestPolicy

    def execute(self, competition_id: str, source_url: str) -> int:
        html = self.http_client.get(source_url)
        matches = self.parser.parse(html, competition_id)
        count = self.uow.matches.upsert_many(matches)
        self.uow.commit()
        return count
