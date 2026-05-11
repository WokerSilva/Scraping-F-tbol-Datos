from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def get(self, url): return "<html></html>"

class Parser:
    def parse_match(self, html, **kwargs):
        class M:
            external_id = "2026239018"
            payload = {"source_match_id": "2026239018", "competition_slug": "clausura_mexico", "round_label": "JORNADA1", "metadata": {"score": "1-2"}, "stats_json": {}, "events_json": []}
        return M()

class Matches:
    def __init__(self): self.calls = 0
    def upsert_match(self, **kwargs): self.calls += 1; return 9

class U:
    matches = Matches()
    raw_pages = type("RP", (), {"save_raw_page": lambda *a, **k: 3})()
    job_runs = type("R", (), {"start_run": lambda *a, **k: 1, "log_event": lambda *a, **k: None, "finish_run": lambda *a, **k: None})()
    scrape_targets = type("S", (), {"mark_transition": lambda *a, **k: True})()
    def commit(self): pass


def test_scrape_match_upserts_single_match():
    uc = ScrapeMatchesUseCase(uow=U(), http_client=Http(), parser=Parser(), request_policy=None)
    uc.execute_match_url(url="https://es.besoccer.com/partido/a/b/2026239018", competition_slug="clausura_mexico")
    assert uc.uow.matches.calls == 1
