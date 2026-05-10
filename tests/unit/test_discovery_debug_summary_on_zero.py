import json
from pathlib import Path

from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class _Team:
    class U:
        class S:
            def upsert_target(self, **kwargs):
                pass
        scrape_targets = S()
        def commit(self):
            pass
    uow = U()


class _Parser:
    def parse(self, html: str):
        return {"matches": []}


class _Browser:
    def render_round_pages(self, **kwargs):
        return [("JORNADA1", "<html></html>")]


class _Http:
    def get(self, url: str) -> str:
        return ""


def test_discovery_debug_summary_saved_on_zero(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    use_case = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    rows = use_case.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False, debug=True)
    assert rows == []
    summary = tmp_path / "data" / "snapshots" / "errors" / "mx_season_clausura_mexico_2026_summary.json"
    assert summary.exists()
    payload = json.loads(summary.read_text(encoding="utf-8"))
    assert "parser_matches_by_round" in payload
