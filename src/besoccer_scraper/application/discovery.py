from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from besoccer_scraper.config.league_catalog import get_league_config
from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import UnitOfWork
from besoccer_scraper.domain.services import build_season_key
from besoccer_scraper.shared.exceptions import HttpFetchError, ScrapeBlockedError


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


@dataclass
class DiscoverMxTeamUseCase:
    uow: UnitOfWork
    http_client: object
    parser: object

    def execute(self, *, competition_slug: str, year: int, team_slug: str, dry_run: bool = True, print_urls: bool = False, persist: bool = False) -> list[dict[str, str]]:
        team_url = f"https://es.besoccer.com/equipo/partidos/{team_slug}/{year}"
        html = self.http_client.get(team_url)
        parsed = self.parser.parse(html, competition_slug)
        discovered: dict[str, dict[str, str]] = {}
        for match in parsed:
            source_match_id = str(match.payload.get("source_match_id") or match.external_id)
            relative_url = str(match.payload.get("relative_url", ""))
            if source_match_id in discovered:
                continue
            discovered[source_match_id] = {"source_match_id": source_match_id, "url": f"https://es.besoccer.com{relative_url}", "competition": competition_slug, "year": str(year), "team": team_slug}
        records = list(discovered.values())
        if persist and not dry_run:
            for record in records:
                self.uow.scrape_targets.insert(source_match_id=record["source_match_id"], source_url=record["url"], status="pending")
            self.uow.commit()
        if print_urls:
            for record in records:
                print(record["url"])
        return records


@dataclass
class DiscoverMxSeasonUseCase:
    team_use_case: DiscoverMxTeamUseCase
    competition_parser: object
    http_client: object
    browser_renderer: object | None = None
    use_browser_fallback: bool = False
    expected_rounds: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.expected_rounds is None:
            self.expected_rounds = {"clausura_mexico": 17, "apertura_mexico": 17}

    def execute(self, *, competition_slug: str, year: int, max_teams: int | None = None, dry_run: bool = True, persist: bool = False, print_urls: bool = False, browser: bool | None = None, fallback_to_teams: bool = True, debug: bool = False) -> list[dict[str, str]]:
        season_key = build_season_key(competition_slug, year)
        competition_url = f"https://es.besoccer.com/competicion/resultados/{competition_slug}/{year}"
        force_browser = competition_slug in {"clausura_mexico", "apertura_mexico"}
        use_browser = force_browser if browser is None else browser
        if browser is None and self.use_browser_fallback:
            use_browser = True

        discovered = self._discover_by_browser(competition_slug, season_key, competition_url, year, debug=debug) if use_browser else self._discover_by_rounds(competition_slug=competition_slug, season_key=season_key, competition_url=competition_url)
        if not discovered and not use_browser and self.use_browser_fallback:
            discovered = self._discover_by_browser(competition_slug, season_key, competition_url, year, debug=debug)
        if fallback_to_teams and self._should_fallback(discovered) and hasattr(self.team_use_case, "execute"):
            discovered = self._discover_by_teams(competition_slug=competition_slug, year=year, season_key=season_key, max_teams=max_teams)

        rows = list(discovered.values())
        if print_urls:
            grouped: dict[str, list[str]] = {}
            for row in rows:
                normalized = self._normalize_round_label(str(row["round_label"]))
                grouped.setdefault(normalized, []).append(row["url"])
            for round_label in sorted(grouped.keys(), key=self._round_sort_key):
                print(f"[{round_label}]")
                for url in grouped[round_label]:
                    print(url)

        detected_rounds_set = {self._normalize_round_label(str(r["round_label"])) for r in rows}
        rounds_detected = len(detected_rounds_set)
        rounds_expected = self.expected_rounds.get(competition_slug, rounds_detected)
        missing_rounds = [f"JORNADA{i}" for i in range(1, rounds_expected + 1) if f"JORNADA{i}" not in detected_rounds_set]
        coverage_status = "complete" if rounds_detected >= rounds_expected and len(rows) >= 140 else "partial"
        print(f"competition={competition_slug} year={year} season_key={season_key} url={competition_url} strategy=browser_competition_rounds rounds_expected={rounds_expected} rounds_detected={rounds_detected} missing_rounds={missing_rounds} targets_found={len(rows)} unique_match_ids={len({r['source_match_id'] for r in rows})} coverage_status={coverage_status} persist={str(persist and not dry_run).lower()}")
        if debug and not rows:
            debug_path = Path("data/snapshots/errors") / f"mx_season_{competition_slug}_{year}_summary.json"
            if debug_path.exists():
                summary = json.loads(debug_path.read_text(encoding="utf-8"))
                print(f"Debug summary: {debug_path}")
                print(f"Debug HTML: {summary.get('after_cookie_html')}")
                print(f"html_length={summary.get('html_length')}")
                print(f"body_text_length={summary.get('body_text_length')}")
                print(f"round_options_found={summary.get('round_options_found')}")
                print(f"match_anchor_count_global={summary.get('match_anchor_count_global')}")
                print(f"match_anchor_count_scoped={summary.get('match_anchor_count_scoped')}")
        if persist and not dry_run and coverage_status == "partial":
            return rows
        if persist and not dry_run:
            for row in rows:
                self.team_use_case.uow.scrape_targets.upsert_target(source_name="besoccer", target_type="match_page", url=row["url"], source_match_id=row["source_match_id"], payload={"source_competition_slug": competition_slug, "season_key": season_key, "round_label": row["round_label"], "status": "pending", "metadata_json": {"discovery_strategy": row["strategy"], "year": year, "source_page_url": competition_url}})
            self.team_use_case.uow.commit()
        return rows

    def _discover_by_rounds(self, *, competition_slug: str, season_key: str, competition_url: str) -> dict[str, dict[str, str]]:
        discovered: dict[str, dict[str, str]] = {}
        try:
            html = self.http_client.get(competition_url)
        except ScrapeBlockedError:
            return discovered
        parsed = self.competition_parser.parse(html)
        rounds = parsed.get("available_rounds", [])
        pages = [competition_url]
        pages.extend(f"{competition_url}/{str(round_label).strip()}" for round_label in rounds if str(round_label).strip())
        for page_url in pages:
            page = self.competition_parser.parse(self.http_client.get(page_url))
            selected_round = str(page.get("selected_round") or "unknown")
            for match in page.get("matches", []):
                source_match_id = str(match.get("source_match_id", "")).strip()
                relative_url = str(match.get("url", "")).strip()
                if not source_match_id or not relative_url or source_match_id in discovered:
                    continue
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": self._canonical_url(relative_url), "source_competition_slug": competition_slug, "season_key": season_key, "round_label": self._normalize_round_label(selected_round), "strategy": "competition_rounds_http", "source_page": page_url}
        return discovered

    def _discover_by_browser(self, competition_slug: str, season_key: str, competition_url: str, year: int, debug: bool = False) -> dict[str, dict[str, str]]:
        if not self.browser_renderer:
            return {}
        discovered: dict[str, dict[str, str]] = {}
        rendered = self.browser_renderer.render_round_pages(url=competition_url, competition=competition_slug, year=year)
        parser_matches_by_round: dict[str, int] = {}
        rounds_attempted = 0
        for round_label, html in rendered:
            rounds_attempted += 1
            page = self.competition_parser.parse(html)
            parser_matches_by_round[round_label] = len(page.get("matches", []))
            for match in page.get("matches", []):
                source_match_id = str(match.get("source_match_id", "")).strip()
                relative_url = str(match.get("url", "")).strip()
                if not source_match_id or not relative_url or source_match_id in discovered:
                    continue
                if not self._is_competition_match(competition_slug, str(match.get("competition_name", ""))):
                    continue
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": self._canonical_url(relative_url), "source_competition_slug": competition_slug, "season_key": season_key, "round_label": self._normalize_round_label(round_label), "strategy": "competition_rounds_browser", "source_page": competition_url}
        if debug:
            base = Path("data/snapshots/errors")
            base.mkdir(parents=True, exist_ok=True)
            summary_path = base / f"mx_season_{competition_slug}_{year}_summary.json"
            initial_html = base / f"mx_season_{competition_slug}_{year}_initial.html"
            after_load_html = base / f"mx_season_{competition_slug}_{year}_after_load.html"
            after_cookie_html = base / f"mx_season_{competition_slug}_{year}_after_cookie.html"
            screenshot = base / f"mx_season_{competition_slug}_{year}_screenshot.png"
            summary_path.write_text(json.dumps({
                "requested_url": competition_url,
                "final_url": competition_url,
                "response_status": None,
                "title": None,
                "html_length": 0,
                "body_text_length": 0,
                "has_round_select": None,
                "has_json_matches": None,
                "match_anchor_count_global": sum(parser_matches_by_round.values()),
                "match_anchor_count_scoped": len(discovered),
                "scope_candidates_found": rounds_attempted,
                "round_options_found": rounds_attempted,
                "rounds_attempted": rounds_attempted,
                "rounds_yielded": len(parser_matches_by_round),
                "parser_matches_by_round": parser_matches_by_round,
                "blocked_domains": [],
                "external_navigation_events": [],
                "initial_html": str(initial_html),
                "after_load_html": str(after_load_html),
                "after_cookie_html": str(after_cookie_html),
                "screenshot": str(screenshot),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        return discovered

    @staticmethod
    def _canonical_url(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("//"):
            return f"https:{url}"
        return f"https://es.besoccer.com{url}"

    @staticmethod
    def _is_competition_match(competition_slug: str, competition_name: str) -> bool:
        name = competition_name.lower()
        expected = {"clausura_mexico": "liga mx - clausura", "apertura_mexico": "liga mx - apertura"}
        token = expected.get(competition_slug)
        return True if not token else token in name

    @staticmethod
    def _normalize_round_label(label: str) -> str:
        text = (label or "").strip().upper()
        match = re.search(r"(\d+)", text)
        if match:
            return f"JORNADA{int(match.group(1))}"
        return text

    @staticmethod
    def _round_sort_key(label: str) -> tuple[int, str]:
        m = re.search(r"(\d+)", label)
        return (int(m.group(1)) if m else 9999, label)

    def _should_fallback(self, discovered: dict[str, dict[str, str]]) -> bool:
        return not discovered

    def _discover_by_teams(self, *, competition_slug: str, year: int, season_key: str, max_teams: int | None) -> dict[str, dict[str, str]]:
        config = get_league_config(competition_slug)
        team_slugs = list(config.get("team_slugs", []))
        if max_teams is not None:
            team_slugs = team_slugs[:max_teams]
        discovered: dict[str, dict[str, str]] = {}
        for team_slug in team_slugs:
            rows = self.team_use_case.execute(competition_slug=competition_slug, year=year, team_slug=str(team_slug), dry_run=True, persist=False)
            for row in rows:
                source_match_id = row["source_match_id"]
                if source_match_id in discovered:
                    continue
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": row["url"], "source_competition_slug": competition_slug, "season_key": season_key, "round_label": "team-fallback", "strategy": "team_matches_fallback", "source_page": f"https://es.besoccer.com/equipo/partidos/{team_slug}/{year}"}
        return discovered
