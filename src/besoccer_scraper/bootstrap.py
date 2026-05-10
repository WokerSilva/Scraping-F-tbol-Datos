from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass

from besoccer_scraper.application.audit import AuditRunUseCase
from besoccer_scraper.application.discovery import DiscoverCompetitionsUseCase, DiscoverMxSeasonUseCase, DiscoverMxTeamUseCase
from besoccer_scraper.application.pipeline import PipelineUseCase
from besoccer_scraper.application.scraping import ScrapeMatchesUseCase
from besoccer_scraper.config.settings import Settings, load_settings
from besoccer_scraper.domain.policies import RequestPolicy, RetryPolicy
from besoccer_scraper.infrastructure.db.connection import DatabaseFactories, build_database_factories
from besoccer_scraper.infrastructure.db.repositories import PostgresUnitOfWork
from besoccer_scraper.infrastructure.http.client import HttpClient
from besoccer_scraper.infrastructure.parsers.competition_parser import CompetitionParser
from besoccer_scraper.infrastructure.parsers.team_matches_parser import TeamMatchesParser


@dataclass
class Container:
    settings: Settings
    db: DatabaseFactories
    uow: PostgresUnitOfWork
    http_client: HttpClient
    competition_parser: CompetitionParser
    matches_parser: TeamMatchesParser
    request_policy: RequestPolicy
    retry_policy: RetryPolicy
    discover_use_case: DiscoverCompetitionsUseCase
    discover_mx_team_use_case: DiscoverMxTeamUseCase
    discover_mx_season_use_case: DiscoverMxSeasonUseCase
    scrape_use_case: ScrapeMatchesUseCase
    audit_use_case: AuditRunUseCase
    pipeline_use_case: PipelineUseCase


def build_container(cli_args: Namespace | None = None) -> Container:
    settings = load_settings(cli_args)

    db = build_database_factories(settings.database_url)
    uow = PostgresUnitOfWork(session=db.session_factory())

    http_client = HttpClient(
        timeout_seconds=settings.http_timeout_seconds,
        user_agent=settings.user_agent,
        max_retries=settings.max_retries,
    )

    competition_parser = CompetitionParser()
    matches_parser = TeamMatchesParser()

    request_policy = RequestPolicy(
        timeout_seconds=settings.http_timeout_seconds,
        user_agent=settings.user_agent,
    )
    retry_policy = RetryPolicy(max_retries=settings.max_retries)

    discover_use_case = DiscoverCompetitionsUseCase(
        uow=uow,
        http_client=http_client,
        parser=competition_parser,
        request_policy=request_policy,
    )
    discover_mx_team_use_case = DiscoverMxTeamUseCase(
        uow=uow,
        http_client=http_client,
        parser=matches_parser,
    )
    discover_mx_season_use_case = DiscoverMxSeasonUseCase(
        team_use_case=discover_mx_team_use_case,
    )

    scrape_use_case = ScrapeMatchesUseCase(
        uow=uow,
        http_client=http_client,
        parser=matches_parser,
        request_policy=request_policy,
    )
    audit_use_case = AuditRunUseCase(uow=uow)
    pipeline_use_case = PipelineUseCase(discover_use_case, scrape_use_case, audit_use_case)

    return Container(
        settings=settings,
        db=db,
        uow=uow,
        http_client=http_client,
        competition_parser=competition_parser,
        matches_parser=matches_parser,
        request_policy=request_policy,
        retry_policy=retry_policy,
        discover_use_case=discover_use_case,
        discover_mx_team_use_case=discover_mx_team_use_case,
        discover_mx_season_use_case=discover_mx_season_use_case,
        scrape_use_case=scrape_use_case,
        audit_use_case=audit_use_case,
        pipeline_use_case=pipeline_use_case,
    )
