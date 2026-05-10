from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class _Parser:
    def parse(self, html: str) -> dict:
        marker = "m1" if "m1" in html else "m2"
        return {"matches": [{"source_match_id": marker, "url": f"/{marker}", "competition_name": "Liga MX - Clausura"}]}


class _Browser:
    def render_round_pages(self, *, url: str, competition: str | None = None, year: int | None = None):
        return [("JORNADA1", "m1"), ("JORNADA2", "m2")]


class _Team:
    def execute(self, **kwargs):
        raise AssertionError("team fallback should not be called in this browser test")


class _Http:
    def get(self, _: str) -> str:
        return ""


def test_discovery_round_assignment_per_match() -> None:
    use_case = DiscoverMxSeasonUseCase(team_use_case=_Team(), competition_parser=_Parser(), http_client=_Http(), browser_renderer=_Browser(), use_browser_fallback=True)
    rows = use_case.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    by_id = {r["source_match_id"]: r for r in rows}
    assert by_id["m1"]["round_label"] == "JORNADA1"
    assert by_id["m2"]["round_label"] == "JORNADA2"
