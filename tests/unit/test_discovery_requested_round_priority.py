from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class _Parser:
    def parse(self, html: str) -> dict:
        return {
            "selected_round": "JORNADA3",
            "matches": [{"source_match_id": "m6", "url": "/partido/a/b/100", "competition_name": "Liga MX - Clausura"}],
            "available_rounds": [],
        }


class _Http:
    def get(self, url: str) -> str:
        return "html"


class _Team:
    def execute(self, **kwargs):
        return []


def test_requested_round_overrides_selected_round_when_mismatch():
    uc = DiscoverMxSeasonUseCase(team_use_case=_Team(), competition_parser=_Parser(), http_client=_Http(), browser_renderer=None, use_browser_fallback=False)
    out = uc._discover_by_rounds(
        competition_slug="clausura_mexico",
        season_key="clausura-2026",
        competition_url="https://es.besoccer.com/competicion/resultados/clausura_mexico/2026/6",
    )
    assert out["m6"]["round_label"] == "JORNADA6"
