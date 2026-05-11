from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class Repo:
    def __init__(self): self.calls = 0
    def upsert_target(self, **kwargs): self.calls += 1; return {"id": self.calls, "inserted": True, "updated": False}
    def count_by_competition_season(self, **kwargs): return self.calls

class U:
    def __init__(self): self.scrape_targets = Repo(); self.commits = 0
    def commit(self): self.commits += 1

class Team:
    def __init__(self): self.uow = U()

class Browser:
    def discover_rounds(self, **kwargs):
        return [{"round_label": "Jornada 1", "matches": [{"source_match_id": "1", "url": "/partido/a/b/1"}]}]

class P: pass
class H: pass


def test_discovery_does_not_persist_partial_without_allow_partial():
    t = Team()
    DiscoverMxSeasonUseCase(t, P(), H(), Browser(), True).execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=False)
    assert t.uow.scrape_targets.calls == 0


def test_discovery_persists_partial_with_allow_partial():
    t = Team()
    DiscoverMxSeasonUseCase(t, P(), H(), Browser(), True).execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=True)
    assert t.uow.scrape_targets.calls == 1
