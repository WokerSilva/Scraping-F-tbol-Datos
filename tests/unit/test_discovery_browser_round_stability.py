import pytest
import besoccer_scraper.application.discovery as discovery_module

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
    def __init__(self, rows=None):
        self.uow = _Uow()
        self._rows = rows or []

    def execute(self, **kwargs):
        return list(self._rows)


class _Parser: ...
class _Http: ...




@pytest.fixture(autouse=True)
def _seed_discovery_globals():
    discovery_module.base_discovered = {}
    discovery_module.missing_rounds = [f"JORNADA{i}" for i in range(1, 18)]

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
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 1}, expected_matches={"clausura_mexico": 1})
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
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 1}, expected_matches={"clausura_mexico": 1})
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=True)
    assert team.uow.scrape_targets.calls[0]["payload"]["status"] == "pending"


def test_existing_target_not_change_round_label():
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [{"round_label": "Jornada 4", "requested_round": "JORNADA4", "matches": [{"source_match_id": "existing", "url": "/partido/a/b/1"}]}]
    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 1}, expected_matches={"clausura_mexico": 1})
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
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 2}, expected_matches={"clausura_mexico": 2})
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
    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 2}, expected_matches={"clausura_mexico": 2})
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    assert {r["round_label"] for r in rows} == {"JORNADA1", "JORNADA3"}
    out = capsys.readouterr().out
    assert "unstable_rounds=['JORNADA2']" in out


def test_dry_run_and_persist_use_same_discovery_result(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(17, 9)

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    dry_rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=True, browser=True, fallback_to_teams=False)
    dry_out = capsys.readouterr().out

    team = _Team()
    uc_persist = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    persist_rows = uc_persist.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False)
    persist_out = capsys.readouterr().out

    assert dry_rows == persist_rows
    assert "persist_requested=false" in dry_out
    assert "persist_applied=false" in dry_out
    assert "persist_requested=true" in persist_out
    assert "persist_applied=true" in persist_out


def test_partial_discovery_does_not_persist_without_allow_partial(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(16, 9)

    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False, allow_partial=False)
    out = capsys.readouterr().out

    assert len(team.uow.scrape_targets.calls) == 0
    assert "persist_requested=true" in out
    assert "persist_applied=false" in out


def test_multipass_union_completes_missing_round(capsys):
    class _Browser:
        def __init__(self):
            self._calls = 0

        def discover_rounds(self, **kwargs):
            self._calls += 1
            if self._calls == 1:
                return _browser_payload(16, 9)
            return _browser_payload(17, 9)

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True, browser_max_passes=2)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out

    assert len(rows) == 153
    assert len({r["source_match_id"] for r in rows}) == 153
    assert "coverage_status=complete" in out


def test_duplicate_match_id_in_two_rounds_is_rejected(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            payload = _browser_payload(17, 9)
            payload[16]["matches"][0]["source_match_id"] = payload[0]["matches"][0]["source_match_id"]
            return payload

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out

    assert len(rows) == 144
    assert "duplicate_source_match_ids=['0101']" in out
    assert "coverage_status=partial" in out


def test_requested_round_mismatch_is_rejected(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            payload = _browser_payload(17, 9)
            payload[16]["requested_round"] = "JORNADA17"
            payload[16]["round_label"] = "Jornada 1"
            return payload

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out

    assert len(rows) == 153
    assert len({r["source_match_id"] for r in rows}) == 153
    assert all(r["round_label"] != "JORNADA1" or r["source_match_id"].startswith("01") for r in rows)
    assert "coverage_status=complete" in out


def test_team_fallback_repairs_missing_rounds(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(16, 9)

    team_rows = [{"source_match_id": f"170{i}", "url": f"https://es.besoccer.com/partido/a/b/170{i}"} for i in range(1, 10)]
    team = _Team(rows=team_rows)
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=True)
    out = capsys.readouterr().out

    repaired = [r for r in rows if r["source_match_id"].startswith("170")]
    assert len(repaired) == 9
    assert {r["round_label"] for r in repaired} == {"JORNADA17"}
    assert "coverage_status=complete" in out


def test_ligamx_complete_result_requires_153_targets(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(17, 9)

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True)
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out

    assert len(rows) == 153
    assert len({r["source_match_id"] for r in rows}) == 153
    assert len({r["round_label"] for r in rows}) == 17
    assert "coverage_status=complete" in out


def test_persist_complete_inserts_153_pending_targets(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return _browser_payload(17, 9)

    team = _Team()
    uc = DiscoverMxSeasonUseCase(team, _Parser(), _Http(), _Browser(), True)
    uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=False, persist=True, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out

    calls = team.uow.scrape_targets.calls
    assert len(calls) == 153
    assert all(c["payload"]["status"] == "pending" for c in calls)
    assert "persist_requested=true" in out
    assert "persist_applied=true" in out


def test_multipass_same_round_same_ids_is_stable(capsys):
    class _Browser:
        def __init__(self):
            self._calls = 0

        def discover_rounds(self, **kwargs):
            self._calls += 1
            return [{"requested_round": "JORNADA1", "matches": [{"source_match_id": "a1", "url": "/partido/a/b/a1"}]}]

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True, browser_max_passes=2, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 1}, expected_matches={"clausura_mexico": 1})
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out
    assert len(rows) == 1
    assert "unstable_rounds=[]" in out


def test_same_match_id_different_round_is_unstable(capsys):
    class _Browser:
        def discover_rounds(self, **kwargs):
            return [
                {"requested_round": "JORNADA1", "matches": [{"source_match_id": "a1", "url": "/partido/a/b/a1"}]},
                {"requested_round": "JORNADA2", "matches": [{"source_match_id": "a1", "url": "/partido/a/b/a1"}]},
            ]

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 2}, expected_matches={"clausura_mexico": 2})
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    out = capsys.readouterr().out
    assert len(rows) == 1
    assert "unstable_rounds=['JORNADA2']" in out


def test_legacy_browser_tuple_result_is_accepted():
    class _Browser:
        def render_round_pages(self, **kwargs):
            return [("JORNADA1", "legacy-html")]

    class _Parser2:
        def parse(self, html):
            assert html == "legacy-html"
            return {"matches": [{"source_match_id": "legacy1", "url": "/partido/a/b/legacy1", "competition_name": "Liga MX - Clausura"}]}

    uc = DiscoverMxSeasonUseCase(_Team(), _Parser2(), _Http(), _Browser(), True, expected_per_round={"clausura_mexico": 1}, expected_rounds={"clausura_mexico": 1}, expected_matches={"clausura_mexico": 1})
    rows = uc.execute(competition_slug="clausura_mexico", year=2026, dry_run=True, persist=False, browser=True, fallback_to_teams=False)
    assert len(rows) == 1
    assert rows[0]["round_label"] == "JORNADA1"
