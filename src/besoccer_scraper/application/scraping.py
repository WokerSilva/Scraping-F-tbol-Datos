from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from besoccer_scraper.domain.enums import TargetStatus
from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import PendingBatchTargetRepository, ScrapeMatchTargetRepository, UnitOfWork
from besoccer_scraper.shared.hashing import sha256_hex


@dataclass
class ScrapeMatchesUseCase:
    uow: UnitOfWork
    http_client: object
    parser: object
    request_policy: RequestPolicy
    save_raw_pages: bool = False
    max_target_attempts: int = 3

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
    ) -> dict[str, Any]:
        targets = self._select_targets(limit=limit)
        counters = {"selected": len(targets), "parsed": 0, "failed": 0, "retry_scheduled": 0, "blocked": 0, "failed_permanent": 0, "skipped_lock": 0, "raw_pages_saved": 0, "matches_upserted": 0}
        run_id = self.uow.job_runs.start_run(job_name="scrape.pending-matches")
        for target in targets:
            target_id = target.get("id")
            target_url = str(target.get("url") or target.get("source_url") or "")
            target_competition = str(target.get("competition_slug") or competition_slug or "unknown")
            if not self._mark_target(target_id, TargetStatus.IN_PROGRESS):
                counters["skipped_lock"] += 1
                continue
            try:
                html = self.http_client.get(target_url)
                if debug_html:
                    debug_path = self._save_debug_html(target=target, html=html)
                    print(f"Debug HTML saved: {debug_path}")
                if self._save_raw_page(target_url, html, enabled=True):
                    counters["raw_pages_saved"] += 1
                parsed_match = self.parser.parse_match(
                    html,
                    url=target_url,
                    competition_slug=target_competition,
                    round_label=target.get("round_label"),
                    season_key=season_key or target.get("season_key"),
                )
                self.uow.matches.upsert_many([parsed_match])
                counters["matches_upserted"] += 1
                self._mark_target(target_id, TargetStatus.PARSED)
                counters["parsed"] += 1
                self.uow.job_runs.log_event(run_id=run_id, event_type="target_parsed", payload={"target_id": target_id, "url": target_url})
            except Exception as exc:  # noqa: BLE001
                status = self._classify_target_failure(target=target, error=str(exc))
                self._mark_target(target_id, status, error=str(exc))
                counters[status.value] += 1
                counters["failed"] += 1
                self.uow.job_runs.log_event(run_id=run_id, event_type="target_failed", payload={"target_id": target_id, "status": status.value, "error": str(exc)})
        self.uow.job_runs.finish_run(run_id=run_id, status="success", stats=counters)
        print(f"selected={counters['selected']}")
        print(f"parsed={counters['parsed']}")
        print(f"failed={counters['failed']}")
        print(f"blocked={counters['blocked']}")
        print(f"retry_scheduled={counters['retry_scheduled']}")
        print(f"raw_pages_saved={counters['raw_pages_saved']}")
        print(f"matches_upserted={counters['matches_upserted']}")
        self.uow.commit()
        return counters

    def execute_match_url(
        self,
        *,
        url: str,
        competition_slug: str,
        round_label: str | None = None,
        debug_html: bool = False,
        target_id: int | None = None,
    ) -> dict[str, Any]:
        run_id = self.uow.job_runs.start_run(job_name="scrape.match")
        html = self.http_client.get(url)
        if debug_html:
            print(html[:1000])
        self._save_raw_page(url, html, enabled=True)
        parsed_match = self.parser.parse_match(
            html,
            url=url,
            competition_slug=competition_slug,
            round_label=round_label,
        )
        self.uow.matches.upsert_many([parsed_match])
        if target_id is not None:
            self._mark_target(target_id, TargetStatus.PARSED)
        payload = parsed_match.payload
        stats_count = len(payload.get("stats_json") or {})
        events_count = len(payload.get("events_json") or [])
        summary = {
            "source_match_id": payload.get("source_match_id"),
            "competition": payload.get("competition_slug"),
            "round": payload.get("round_label"),
            "score": (payload.get("metadata") or {}).get("score"),
            "stats_count": stats_count,
            "events_count": events_count,
        }
        self.uow.job_runs.log_event(run_id=run_id, event_type="match_parsed", payload=summary)
        self.uow.job_runs.finish_run(run_id=run_id, status="success", stats=summary)
        print(f"match summary: source_match_id={summary['source_match_id']} competition={summary['competition']} round={summary['round']} score={summary['score']} stats_count={stats_count} events_count={events_count}")
        self.uow.commit()
        return summary

    def _select_targets(self, *, limit: int) -> list[dict[str, Any]]:
        repository: PendingBatchTargetRepository = self.uow.scrape_targets
        return list(repository.list_for_processing(limit=limit))

    def _mark_target(self, target_id: Any, status: TargetStatus, error: str | None = None) -> bool:
        repository: ScrapeMatchTargetRepository = self.uow.scrape_targets
        target_int = int(target_id)
        if status == TargetStatus.IN_PROGRESS:
            return repository.mark_transition(
                target_id=target_int,
                from_statuses=("pending", "discovered", "retry_scheduled"),
                to_status="in_progress",
            )
        if status == TargetStatus.PARSED:
            return repository.mark_transition(
                target_id=target_int,
                from_statuses=("in_progress",),
                to_status="parsed",
            )
        if status == TargetStatus.BLOCKED:
            return repository.mark_transition(
                target_id=target_int,
                from_statuses=("in_progress",),
                to_status="blocked",
                error=error,
            )
        if status == TargetStatus.RETRY_SCHEDULED:
            return repository.mark_transition(
                target_id=target_int,
                from_statuses=("in_progress",),
                to_status="retry_scheduled",
                error=error,
            )
        if status == TargetStatus.FAILED_PERMANENT:
            return repository.mark_transition(
                target_id=target_int,
                from_statuses=("in_progress",),
                to_status="failed_permanent",
                error=error or "unknown error",
            )
        raise ValueError(f"Unsupported target status transition to {status.value}")

    def _save_raw_page(self, url: str, html: str, *, enabled: bool) -> bool:
        if not enabled:
            return False
        payload = {
            "source_name": "besoccer",
            "url": url,
            "body": html,
            "body_hash": sha256_hex(html),
            "status_code": 200,
            "fetched_at": datetime.now(timezone.utc),
        }
        self.uow.raw_pages.save_raw_page(
            source_name=payload["source_name"],
            url=payload["url"],
            content_hash=payload["body_hash"],
            body=payload["body"],
            status_code=payload["status_code"],
            metadata={"fetched_at": payload["fetched_at"].isoformat()},
        )
        return True

    def _save_debug_html(self, *, target: dict[str, Any], html: str) -> str:
        source_match_id = str(target.get("source_match_id") or target.get("id") or "unknown")
        path = Path("data/snapshots/match_pages") / f"match_{source_match_id}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return str(path)

    def _is_raw_enabled(self) -> bool:
        return self.save_raw_pages or str(os.getenv("SAVE_RAW_PAGES", "")).strip().lower() in {"1", "true", "yes", "on"}

    def _classify_target_failure(self, *, target: dict[str, Any], error: str) -> TargetStatus:
        lowered = error.lower()
        if any(token in lowered for token in ("403", "406", "429", "captcha", "challenge", "forbidden", "blocked")):
            return TargetStatus.BLOCKED
        attempt = int((target.get("payload") or {}).get("attempt_count", 0)) + 1
        if attempt >= self.max_target_attempts:
            return TargetStatus.FAILED_PERMANENT
        return TargetStatus.RETRY_SCHEDULED
