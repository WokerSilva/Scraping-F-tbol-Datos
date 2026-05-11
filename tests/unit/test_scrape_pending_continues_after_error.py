from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def __init__(self): self.i = 0
    def get(self, url):
        self.i += 1
        if self.i == 1:
            raise RuntimeError("403 forbidden")
        return "<html>ok</html>"

class Parser:
    def parse_match(self, html, **kwargs):
        class M:
            payload = {"stats_json": {}, "events_json": {}}
        return M()

class Targets:
    def list_for_processing(self, *, limit):
        return [{"id": 1, "url": "u1", "payload": {}}, {"id": 2, "url": "u2", "payload": {}}]
    def mark_transition(self, **kwargs): return True

class Runs:
    def start_run(self, **kwargs): return 1
    def log_event(self, **kwargs): pass
    def finish_run(self, **kwargs): pass

class Matches:
    def upsert_many(self, items): return 1

class U:
    scrape_targets = Targets()
    job_runs = Runs()
    matches = Matches()
    raw_pages = type("R", (), {"save_raw_page": lambda *a, **k: 1})()
    def commit(self): pass


def test_pending_continues_after_error():
    out = ScrapeMatchesUseCase(uow=U(), http_client=Http(), parser=Parser(), request_policy=None).execute_pending_matches(limit=2)
    assert out["blocked"] == 1
    assert out["parsed"] == 1
