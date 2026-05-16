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
        return {
            "matches": [
                {
                    "source_match_id": "100",
                    "url": "/partido/club-a/club-b/100",
                    "competition_name": "Liga MX - Clausura",
                }
            ]
        }


class _Browser:
    def discover_rounds(self, **kwargs):
        return [
            {
                "requested_round": "Jornada 1",
                "matches": [
                    {
                        "source_match_id": "100",
                        "url": "/partido/club-a/club-b/100",
                        "competition_name": "Liga MX - Clausura",
                    }
                ],
                "diagnostics": {"status_reason": "ok"},
            }
        ]


class _Http:
    def get(self, u):
        return ""


def test_discover_by_browser_does_not_raise_nameerror() -> None:
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)

    discovered = uc._discover_by_browser(
        competition_slug="clausura_mexico",
        season_key="2026",
        competition_url="https://es.besoccer.com/competicion/clasificacion/clausura_mexico/2026",
        year=2026,
        debug=False,
    )

    assert discovered["100"]["source_match_id"] == "100"


def test_execute_browser_path_does_not_raise_nameerror() -> None:
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)

    rows = uc.execute(
        competition_slug="clausura_mexico",
        year=2026,
        dry_run=True,
        persist=False,
        browser=True,
        fallback_to_teams=False,
    )

    assert any(row["source_match_id"] == "100" for row in rows)
