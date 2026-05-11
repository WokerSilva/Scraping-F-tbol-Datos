from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


def _mk(rounds, matches):
    out = []
    for r in range(1, rounds + 1):
        round_matches = []
        for i in range(matches // rounds):
            mid = f"{r}{i:03d}"
            round_matches.append({"source_match_id": mid, "url": f"/partido/a/b/{mid}"})
        out.append({"round_label": f"Jornada {r}", "matches": round_matches})
    return out

class _Browser:
    def __init__(self, data): self.data = data
    def discover_rounds(self, **kwargs): return self.data
class _Team:
    class U:
        class S:
            def upsert_target(self, **kwargs): pass
        scrape_targets = S()
        def commit(self): pass
    uow = U()
class _Parser: pass
class _Http: pass


def test_coverage_complete(capsys):
    DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(_mk(17, 153)), True).execute(competition_slug="clausura_mexico", year=2026, dry_run=True, browser=True, fallback_to_teams=False)
    assert "coverage_status=complete" in capsys.readouterr().out


def test_coverage_partial(capsys):
    DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(_mk(10, 90)), True).execute(competition_slug="clausura_mexico", year=2026, dry_run=True, browser=True, fallback_to_teams=False)
    assert "coverage_status=partial" in capsys.readouterr().out
