import pytest

from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class _Team:
    def execute(self, **kwargs):
        return []


class _Browser:
    def discover_rounds(self, **kwargs):
        return [{"round_label": "Jornada 1", "matches": [{"source_match_id": "1", "url": "/partido/a/b/1"}]}]


class _Parser:
    pass


class _Http:
    pass


def test_discovery_require_complete_fails_on_partial():
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    with pytest.raises(RuntimeError):
        uc.execute(
            competition_slug="clausura_mexico",
            year=2026,
            dry_run=True,
            persist=False,
            browser=True,
            fallback_to_teams=False,
            require_complete=True,
        )
