from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class _Browser:
    def discover_rounds(self, **kwargs):
        return [{"round_label": "Jornada 1", "matches": [{"source_match_id": "1", "url": "/partido/a/b/1"}]}]


class _Team:
    class U:
        class S:
            def upsert_target(self, **kwargs):
                pass
        scrape_targets = S()
        def commit(self):
            pass
    uow = U()


class _Parser: pass
class _Http: pass


def test_default_output_is_summary(capsys):
    DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True).execute(competition_slug="clausura_mexico", year=2026, dry_run=True, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out
    assert "coverage_status=" in out
    assert "https://" not in out
