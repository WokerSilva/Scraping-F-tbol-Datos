from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from besoccer_scraper.domain.enums import TargetStatus
from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import UnitOfWork
from besoccer_scraper.shared.hashing import sha256_hex


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

    def execute_pending_matches(
        self,
        *,
        competition_slug: str | None = None,
        season_key: str | None = None,
        limit: int = 20,
        debug_html: bool = False,
    ) -> int:
        targets = self._select_targets(limit=limit)
        parsed_total = 0
        for target in targets:
            target_id = target.get("id")
            target_url = str(target.get("url") or target.get("source_url") or "")
            target_competition = str(target.get("competition_slug") or competition_slug or "unknown")
            self._mark_target(target_id, TargetStatus.IN_PROGRESS)
            try:
                html = self.http_client.get(target_url)
                if debug_html:
                    print(html[:1000])
                self._save_raw_page(target_url, html)
                parsed_match = self.parser.parse_match(
                    html,
                    url=target_url,
                    competition_slug=target_competition,
                    round_label=target.get("round_label"),
                    season_key=season_key or target.get("season_key"),
                )
                self.uow.matches.upsert_many([parsed_match])
                self._mark_target(target_id, TargetStatus.PARSED)
                parsed_total += 1
            except Exception as exc:  # noqa: BLE001
                self._mark_target(target_id, TargetStatus.FAILED, error=str(exc))
        self.uow.commit()
        return parsed_total

    def execute_match_url(
        self,
        *,
        url: str,
        competition_slug: str,
        round_label: str | None = None,
        debug_html: bool = False,
    ) -> int:
        html = self.http_client.get(url)
        if debug_html:
            print(html[:1000])
        self._save_raw_page(url, html)
        parsed_match = self.parser.parse_match(
            html,
            url=url,
            competition_slug=competition_slug,
            round_label=round_label,
        )
        self.uow.matches.upsert_many([parsed_match])
        self.uow.commit()
        return 1

    def _select_targets(self, *, limit: int) -> list[dict[str, Any]]:
        repository = self.uow.scrape_targets
        if hasattr(repository, "select_pending"):
            return list(repository.select_pending(limit=limit))
        return []

    def _mark_target(self, target_id: Any, status: TargetStatus, error: str | None = None) -> None:
        repository = self.uow.scrape_targets
        if hasattr(repository, "mark_status"):
            repository.mark_status(target_id=target_id, status=status.value, error=error)

    def _save_raw_page(self, url: str, html: str) -> None:
        payload = {
            "source_name": "besoccer",
            "url": url,
            "body": html,
            "body_hash": sha256_hex(html),
            "status_code": 200,
            "fetched_at": datetime.now(timezone.utc),
        }
        if hasattr(self.uow.raw_pages, "insert"):
            self.uow.raw_pages.insert(**payload)
