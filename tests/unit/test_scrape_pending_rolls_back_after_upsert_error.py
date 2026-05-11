from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def get(self, url): return "<html></html>"

class Parser:
    def parse_match(self, html, **kwargs):
        class M:
            external_id = "2026"
            payload = {"source_match_id": "2026", "metadata": {}, "stats_json": {}, "events_json": []}
        return M()

class Matches:
    def ensure_source(self, name="besoccer"): return 2
    def upsert_match(self, **kwargs): raise RuntimeError("fk fail")

class Targets:
    def list_for_processing(self, *, limit): return [{"id": 1, "url": "u", "payload": {}}]
    def mark_transition(self, **kwargs): return True

class Session:
    def __init__(self): self.rolled = False
    def rollback(self): self.rolled = True

class U:
    def __init__(self):
        self.matches = Matches(); self.scrape_targets = Targets(); self.session = Session()
        self.raw_pages = type("RP", (), {"save_raw_page": lambda *a, **k: 1})()
        self.job_runs = type("R", (), {"start_run": lambda *a, **k: 1, "log_event": lambda *a, **k: None, "finish_run": lambda *a, **k: None})()
    def commit(self): pass


def test_pending_rolls_back_after_upsert_error():
    u = U()
    out = ScrapeMatchesUseCase(uow=u, http_client=Http(), parser=Parser(), request_policy=None).execute_pending_matches(limit=1)
    assert u.session.rolled is True
    assert out["retry_scheduled"] == 1
