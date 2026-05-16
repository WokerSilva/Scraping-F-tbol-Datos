from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


class _Repo:
    def __init__(self):
        self.calls = []

    def upsert_target(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["source_match_id"] == "existing":
            return {"inserted": False, "updated": False, "updated_safe": True, "skipped_existing": True}
        return {"inserted": True, "updated": False, "updated_safe": False, "skipped_existing": False}

    def count_by_competition_season(self, **kwargs):
        return len(self.calls)


class _Uow:
    def __init__(self):
        self.scrape_targets = _Repo()
    def commit(self): ...


class _Team:
    def __init__(self):
        self.uow = _Uow()
    def execute(self, **kwargs):
        return []


class _Parser: ...
class _Http: ...


def _browser_payload(rounds: int, per_round: int):
    out = []
    for r in range(1, rounds + 1):
        matches = [{"source_match_id": f"{r:02d}{i:02d}", "url": f"/partido/a/b/{r:02d}{i:02d}"} for i in range(1, per_round + 1)]
        out.append({"round_label": f"Jornada {r}", "requested_round": f"JORNADA{r}", "matches": matches})
    return out


def test_browser_round_iteration_assigns_requested_round_label():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [{"round_label": "Jornada 3", "requested_round": "JORNADA6", "matches": [{"source_match_id": "m6", "url": "/partido/a/b/100"}]}]
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    out = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    assert out[0]["round_label"] == "JORNADA6"


def test_discovery_blocks_persist_when_incomplete_without_allow_partial():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(16, 9)
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=False)
    assert team.uow.scrape_targets.calls == []


def test_discovery_complete_17_rounds_153_matches(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(17, 9)
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    assert "coverage_status=complete" in capsys.readouterr().out


def test_existing_target_not_reset_status():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [{"round_label": "Jornada 1", "requested_round": "JORNADA1", "matches": [{"source_match_id": "existing", "url": "/partido/a/b/1"}]}]
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=True)
    assert team.uow.scrape_targets.calls[0]["payload"]["status"] == "pending"


def test_existing_target_not_change_round_label():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [{"round_label": "Jornada 4", "requested_round": "JORNADA4", "matches": [{"source_match_id": "existing", "url": "/partido/a/b/1"}]}]
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=True)
    assert team.uow.scrape_targets.calls[0]["payload"]["round_label"] == "JORNADA4"


def test_discovery_reports_missing_jornada17_when_absent(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(16, 9)
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out
    assert "missing_rounds=['JORNADA17']" in out


def test_discovery_jornada17_after_retry_counts_complete(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            data = _browser_payload(16, 9)
            data.append(
                {
                    "round_label": "Jornada 17",
                    "requested_round": "JORNADA17",
                    "diagnostics": {"status_reason": "ok", "attempts": 2},
                    "matches": [{"source_match_id": f"17{i:02d}", "url": f"/partido/a/b/17{i:02d}"} for i in range(1, 10)],
                }
            )
            return data
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out
    assert "JORNADA17 count=9" in out
    assert "coverage_status=complete" in out


def test_partial_discovery_is_not_persisted_without_allow_partial():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(16, 9)
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=False)
    assert len(team.uow.scrape_targets.calls) == 0


def test_discovery_result_complete_is_persisted_atomically():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(17, 9)
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=False)
    assert len(team.uow.scrape_targets.calls) == 153


def test_requested_round_label_wins_only_when_dom_changed(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            data = _browser_payload(16, 9)
            data.append(
                {
                    "round_label": "Jornada 17",
                    "requested_round": "JORNADA17",
                    "diagnostics": {"status_reason": "same_as_previous_round"},
                    "matches": [{"source_match_id": "1601", "url": "/partido/a/b/1601"}],
                }
            )
            return data
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    assert all(r["round_label"] != "JORNADA17" for r in rows)
    out = capsys.readouterr().out
    assert "unstable_rounds=['JORNADA17']" in out


def test_persist_does_not_relabel_jornada17_as_jornada1():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [
                {"round_label": "JORNADA1", "requested_round": "JORNADA1", "diagnostics": {"status_reason": "ok"}, "matches": [{"source_match_id": "m1", "url": "/partido/a/b/1"}]},
                {"round_label": "JORNADA17", "requested_round": "JORNADA17", "diagnostics": {"status_reason": "ok"}, "matches": [{"source_match_id": "m17", "url": "/partido/a/b/17"}]},
            ]
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=True)
    payload_by_id = {c["source_match_id"]: c["payload"]["round_label"] for c in team.uow.scrape_targets.calls}
    assert payload_by_id["m1"] == "JORNADA1"
    assert payload_by_id["m17"] == "JORNADA17"


def test_round_is_retried_when_ids_equal_previous_round(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [
                {"round_label": "JORNADA1", "requested_round": "JORNADA1", "diagnostics": {"status_reason": "ok", "attempts": 1}, "matches": [{"source_match_id": "a1", "url": "/partido/a/b/a1"}]},
                {"round_label": "JORNADA2", "requested_round": "JORNADA2", "diagnostics": {"status_reason": "same_as_previous_round", "attempts": 3}, "matches": [{"source_match_id": "a1", "url": "/partido/a/b/a1"}]},
                {"round_label": "JORNADA3", "requested_round": "JORNADA3", "diagnostics": {"status_reason": "ok", "attempts": 2}, "matches": [{"source_match_id": "a3", "url": "/partido/a/b/a3"}]},
            ]
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    assert {r["round_label"] for r in rows} == {"JORNADA1", "JORNADA3"}
    out = capsys.readouterr().out
    assert "unstable_rounds=['JORNADA2']" in out
