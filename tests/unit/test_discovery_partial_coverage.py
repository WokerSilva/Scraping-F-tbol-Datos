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
    def execute(self, **kwargs):
        return []


class _Parser:
    def parse(self, html):
        return {"matches": [{"source_match_id": "1", "url": "/partido/a/b/1", "competition_name": "Liga MX - Clausura"}]}


class _Browser:
    def render_round_pages(self, **kwargs):
        return [("JORNADA1", "x")]


class _Http:
    def get(self, u):
        return ""


def test_discovery_partial_coverage() -> None:
    rows = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True).execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True)
    assert len(rows) == 1
