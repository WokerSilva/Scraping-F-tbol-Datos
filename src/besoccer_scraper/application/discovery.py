from __future__ import annotations

from dataclasses import dataclass

from besoccer_scraper.config.league_catalog import get_league_config
from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import UnitOfWork
from besoccer_scraper.domain.services import build_season_key


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

    def execute(
        self,
        *,
        competition_slug: str,
        year: int,
        team_slug: str,
        dry_run: bool = True,
        print_urls: bool = False,
        persist: bool = False,
    ) -> list[dict[str, str]]:
        team_url = f"https://es.besoccer.com/equipo/partidos/{team_slug}/{year}"
        html = self.http_client.get(team_url)
        parsed = self.parser.parse(html, competition_slug)

        discovered: dict[str, dict[str, str]] = {}
        for match in parsed:
            source_match_id = str(match.payload.get("source_match_id") or match.external_id)
            relative_url = str(match.payload.get("relative_url", ""))
            if source_match_id in discovered:
                continue
            discovered[source_match_id] = {
                "source_match_id": source_match_id,
                "url": f"https://es.besoccer.com{relative_url}",
                "competition": competition_slug,
                "year": str(year),
                "team": team_slug,
            }

        records = list(discovered.values())

        if persist and not dry_run:
            for record in records:
                self.uow.scrape_targets.insert(
                    source_match_id=record["source_match_id"],
                    source_url=record["url"],
                    status="pending",
                )
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

    def execute(
        self,
        *,
        competition_slug: str,
        year: int,
        max_teams: int | None = None,
        dry_run: bool = True,
        persist: bool = False,
        print_urls: bool = False,
    ) -> list[dict[str, str]]:
        season_key = build_season_key(competition_slug, year)
        competition_url = f"https://es.besoccer.com/competicion/resultados/{competition_slug}/{year}"

        discovered = self._discover_by_rounds(
            competition_slug=competition_slug,
            season_key=season_key,
            competition_url=competition_url,
        )

        if self._should_fallback(discovered):
            print(
                "WARNING: Falling back to team strategy (reason: no rounds, less than 100 matches, or anti-bot/challenge detected)."
            )
            discovered = self._discover_by_teams(
                competition_slug=competition_slug,
                year=year,
                season_key=season_key,
                max_teams=max_teams,
            )

        rows = list(discovered.values())

        if print_urls:
            grouped: dict[str, list[str]] = {}
            for row in rows:
                grouped.setdefault(row["round_label"], []).append(row["url"])
            for round_label in sorted(grouped.keys()):
                print(f"[{round_label}]")
                for url in grouped[round_label]:
                    print(url)

        if persist and not dry_run:
            for row in rows:
                self.team_use_case.uow.scrape_targets.upsert_target(
                    source_name="besoccer",
                    target_type="match_page",
                    url=row["url"],
                    source_match_id=row["source_match_id"],
                    payload={
                        "competition": competition_slug,
                        "source_competition_slug": competition_slug,
                        "season_key": season_key,
                        "round_label": row["round_label"],
                        "strategy": row["strategy"],
                        "source_page": row["source_page"],
                        "metadata_json": {
                            "strategy": row["strategy"],
                            "source_page": row["source_page"],
                        },
                        "status": "pending",
                    },
                )
            self.team_use_case.uow.commit()
        return rows

    def _discover_by_rounds(self, *, competition_slug: str, season_key: str, competition_url: str) -> dict[str, dict[str, str]]:
        discovered: dict[str, dict[str, str]] = {}
        html = self.http_client.get(competition_url)
        parsed = self.competition_parser.parse(html)
        rounds = parsed.get("available_rounds", [])
        pages = [competition_url]
        pages.extend(f"{competition_url}/{str(round_label).strip()}" for round_label in rounds if str(round_label).strip())

        for page_url in pages:
            rendered_html = self.http_client.get(page_url)
            page = self.competition_parser.parse(rendered_html)
            selected_round = str(page.get("selected_round") or "unknown")
            for match in page.get("matches", []):
                source_match_id = str(match.get("source_match_id", "")).strip()
                relative_url = str(match.get("url", "")).strip()
                if not source_match_id or not relative_url:
                    continue
                if source_match_id in discovered:
                    continue
                discovered[source_match_id] = {
                    "source_match_id": source_match_id,
                    "url": f"https://es.besoccer.com{relative_url}",
                    "source_competition_slug": competition_slug,
                    "season_key": season_key,
                    "round_label": selected_round,
                    "strategy": "competition_rounds_render",
                    "source_page": page_url,
                }
        return discovered

    def _should_fallback(self, discovered: dict[str, dict[str, str]]) -> bool:
        if not discovered:
            return True
        has_unknown_rounds = all(row.get("round_label") in (None, "", "unknown") for row in discovered.values())
        less_than_minimum = len(discovered) < 100
        challenge_block = any("challenge" in row.get("source_page", "").lower() for row in discovered.values())
        return has_unknown_rounds or less_than_minimum or challenge_block

    def _discover_by_teams(
        self,
        *,
        competition_slug: str,
        year: int,
        season_key: str,
        max_teams: int | None,
    ) -> dict[str, dict[str, str]]:
        config = get_league_config(competition_slug)
        team_slugs = list(config.get("team_slugs", []))
        if max_teams is not None:
            team_slugs = team_slugs[:max_teams]

        discovered: dict[str, dict[str, str]] = {}
        for team_slug in team_slugs:
            rows = self.team_use_case.execute(
                competition_slug=competition_slug,
                year=year,
                team_slug=str(team_slug),
                dry_run=True,
                persist=False,
            )
            for row in rows:
                source_match_id = row["source_match_id"]
                if source_match_id in discovered:
                    continue
                discovered[source_match_id] = {
                    "source_match_id": source_match_id,
                    "url": row["url"],
                    "source_competition_slug": competition_slug,
                    "season_key": season_key,
                    "round_label": "team-fallback",
                    "strategy": "team_matches_fallback",
                    "source_page": f"https://es.besoccer.com/equipo/partidos/{team_slug}/{year}",
                }
        return discovered
