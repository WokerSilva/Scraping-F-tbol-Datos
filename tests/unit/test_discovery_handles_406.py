from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase
from besoccer_scraper.shared.exceptions import ScrapeBlockedError


class _Http:
    def get(self, _: str) -> str:
        raise ScrapeBlockedError("blocked", status_code=406)


class _Parser:
    def parse(self, html: str) -> dict:
        return {"matches": [{"source_match_id": "mx1", "url": "/partido/mx1", "competition_name": "Liga MX - Clausura"}]}


class _Browser:
    def render_round_pages(self, *, url: str, competition: str | None = None, year: int | None = None):
        yield ("JORNADA1", "<html></html>")


class _Team:
    def execute(self, **kwargs):
        return []


def test_discovery_uses_browser_fallback_on_406() -> None:
    use_case = DiscoverMxSeasonUseCase(team_use_case=_Team(), competition_parser=_Parser(), http_client=_Http(), browser_renderer=_Browser(), use_browser_fallback=True)
    rows = use_case.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=False, fallback_to_teams=False)
    assert rows
    assert rows[0]["source_match_id"] == "mx1"
    assert rows[0]["round_label"] == "JORNADA1"
