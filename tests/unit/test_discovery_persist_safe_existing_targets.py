from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class Repo:
    def __init__(self):
        self.calls = []

    def upsert_target(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["source_match_id"] == "existing":
            return {"id": 1, "inserted": False, "updated": False, "updated_safe": True, "skipped_existing": True}
        return {"id": 2, "inserted": True, "updated": False, "updated_safe": False, "skipped_existing": False}

    def count_by_competition_season(self, **kwargs):
        return 2


class U:
    def __init__(self):
        self.scrape_targets = Repo()
        self.commits = 0

    def commit(self):
        self.commits += 1


class Team:
    def __init__(self):
        self.uow = U()


class Browser:
    def discover_rounds(self, **kwargs):
        return [{"round_label": "Jornada 1", "matches": [
            {"source_match_id": "existing", "url": "/partido/a/b/1"},
            {"source_match_id": "new", "url": "/partido/a/b/2"},
        ]}]


class P:
    pass


class H:
    pass


def test_discovery_summary_distinguishes_inserted_skipped_and_updated_safe(capsys):
    t = Team()
    DiscoverMxSeasonUseCase(t, P(), H(), Browser(), True).execute(
        competition_slug="clausura_mexico",
        year=2026,
        dry_run=False,
        persist=True,
        browser=True,
        fallback_to_teams=False,
        allow_partial=True,
    )
    out = capsys.readouterr().out
    assert "inserted=1" in out
    assert "updated=0" in out
    assert "updated_safe=1" in out
    assert "skipped_existing=1" in out


def test_new_target_inserted_as_pending_payload():
    t = Team()
    DiscoverMxSeasonUseCase(t, P(), H(), Browser(), True).execute(
        competition_slug="clausura_mexico",
        year=2026,
        dry_run=False,
        persist=True,
        browser=True,
        fallback_to_teams=False,
        allow_partial=True,
    )
    pending_statuses = [c["payload"]["status"] for c in t.uow.scrape_targets.calls if c["source_match_id"] == "new"]
    assert pending_statuses == ["pending"]
