from __future__ import annotations

from dataclasses import dataclass

from besoccer_scraper.config.league_catalog import get_league_config
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
            if competition_slug.split("_")[0] not in relative_url and competition_slug not in relative_url:
                # best-effort filter by competition name if present in URL
                pass
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

    def execute(
        self,
        *,
        competition_slug: str,
        year: int,
        max_teams: int | None = None,
        dry_run: bool = True,
        persist: bool = False,
    ) -> list[dict[str, str]]:
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
                dry_run=dry_run,
                persist=False,
            )
            for row in rows:
                discovered[row["source_match_id"]] = row

        records = list(discovered.values())
        if persist and not dry_run:
            for record in records:
                self.team_use_case.uow.scrape_targets.insert(
                    source_match_id=record["source_match_id"],
                    source_url=record["url"],
                    status="pending",
                )
            self.team_use_case.uow.commit()
        return records
