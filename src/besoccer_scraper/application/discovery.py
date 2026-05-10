from __future__ import annotations

from dataclasses import dataclass

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

    def execute(self, *, competition_slug: str, year: int, max_teams: int | None = None, dry_run: bool = True, persist: bool = False, print_urls: bool = False, browser: bool | None = None) -> list[dict[str, str]]:
        season_key = build_season_key(competition_slug, year)
        competition_url = f"https://es.besoccer.com/competicion/resultados/{competition_slug}/{year}"
        force_browser = competition_slug in {"clausura_mexico", "apertura_mexico"}
        use_browser = force_browser if browser is None else browser
        if browser is None and self.use_browser_fallback:
            use_browser = True

        discovered = self._discover_by_browser(competition_slug, season_key, competition_url, year) if use_browser else self._discover_by_rounds(competition_slug=competition_slug, season_key=season_key, competition_url=competition_url)
        if not discovered and not use_browser and self.use_browser_fallback:
            discovered = self._discover_by_browser(competition_slug, season_key, competition_url, year)
        if self._should_fallback(discovered):
            discovered = self._discover_by_teams(competition_slug=competition_slug, year=year, season_key=season_key, max_teams=max_teams)

        rows = list(discovered.values())
        if print_urls:
            grouped: dict[str, list[str]] = {}
            for row in rows:
                grouped.setdefault(row["round_label"], []).append(row["url"])
            for round_label in sorted(grouped.keys()):
                print(f"[{round_label}]")
                for url in grouped[round_label]:
                    print(url)

        print(f"competition={competition_slug} year={year} season_key={season_key} url={competition_url} strategy=browser_competition_rounds rounds_detected={len(set(r['round_label'] for r in rows))} targets_found={len(rows)} unique_match_ids={len({r['source_match_id'] for r in rows})} persist={str(persist and not dry_run).lower()}")
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
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": f"https://es.besoccer.com{relative_url}", "source_competition_slug": competition_slug, "season_key": season_key, "round_label": selected_round, "strategy": "competition_rounds_http", "source_page": page_url}
        return discovered

    def _discover_by_browser(self, competition_slug: str, season_key: str, competition_url: str, year: int) -> dict[str, dict[str, str]]:
        if not self.browser_renderer:
            return {}
        discovered: dict[str, dict[str, str]] = {}
        for round_label, html in self.browser_renderer.render_round_pages(url=competition_url, competition=competition_slug, year=year):
            page = self.competition_parser.parse(html)
            for match in page.get("matches", []):
                source_match_id = str(match.get("source_match_id", "")).strip()
                relative_url = str(match.get("url", "")).strip()
                if not source_match_id or not relative_url or source_match_id in discovered:
                    continue
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": f"https://es.besoccer.com{relative_url}", "source_competition_slug": competition_slug, "season_key": season_key, "round_label": round_label, "strategy": "competition_rounds_browser", "source_page": competition_url}
        return discovered

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
