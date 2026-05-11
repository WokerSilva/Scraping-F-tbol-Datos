from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def get(self, url): return "<html>ok</html>"

class Parser:
    def parse_match(self, html, **kwargs): raise RuntimeError("parse fail")

class Targets:
    def list_for_processing(self, *, limit): return [{"id": 1, "url": "u1", "payload": {}}]
    def mark_transition(self, **kwargs): return True

class Raw:
    def __init__(self): self.calls = 0
    def save_raw_page(self, **kwargs): self.calls += 1; return 1

class Runs:
    def start_run(self, **kwargs): return 1
    def log_event(self, **kwargs): pass
    def finish_run(self, **kwargs): pass

class U:
    def __init__(self):
        self.scrape_targets = Targets(); self.raw_pages = Raw(); self.job_runs = Runs(); self.matches = type("M", (), {"upsert_many": lambda *a, **k: 1})()
    def commit(self): pass


def test_scrape_saves_raw_before_parse():
    u = U()
    out = ScrapeMatchesUseCase(uow=u, http_client=Http(), parser=Parser(), request_policy=None).execute_pending_matches(limit=1)
    assert u.raw_pages.calls == 1
    assert out["retry_scheduled"] == 1
