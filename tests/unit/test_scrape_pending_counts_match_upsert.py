from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def get(self, url): return "<html>x</html>"

class Parser:
    def parse_match(self, html, **kwargs):
        class M:
            payload = {}
        return M()

class T:
    def list_for_processing(self, *, limit): return [{"id": 1, "url": "u1", "payload": {}}]
    def mark_transition(self, **kwargs): return True

class U:
    scrape_targets = T()
    job_runs = type("R", (), {"start_run": lambda *a, **k: 1, "log_event": lambda *a, **k: None, "finish_run": lambda *a, **k: None})()
    raw_pages = type("RP", (), {"save_raw_page": lambda *a, **k: 1})()
    matches = type("M", (), {"upsert_many": lambda *a, **k: 1})()
    def commit(self): pass


def test_pending_counts_match_upsert():
    out = ScrapeMatchesUseCase(uow=U(), http_client=Http(), parser=Parser(), request_policy=None).execute_pending_matches(limit=1)
    assert out["matches_upserted"] == 1
