from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def get(self, url): return "<html><body>PRIVATE_HTML_CONTENT</body></html>"

class Parser:
    def parse_match(self, html, **kwargs):
        class M:
            payload = {"stats_json": {}, "events_json": {}}
        return M()

class Targets:
    def list_for_processing(self, *, limit): return [{"id": 1, "source_match_id": "123", "url": "u1", "payload": {}}]
    def mark_transition(self, **kwargs): return True

class Runs:
    def start_run(self, **kwargs): return 1
    def log_event(self, **kwargs): pass
    def finish_run(self, **kwargs): pass

class U:
    scrape_targets = Targets()
    job_runs = Runs()
    matches = type("M", (), {"upsert_many": lambda *a, **k: 1})()
    raw_pages = type("R", (), {"save_raw_page": lambda *a, **k: 1})()
    def commit(self): pass


def test_debug_html_saved_not_printed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ScrapeMatchesUseCase(uow=U(), http_client=Http(), parser=Parser(), request_policy=None).execute_pending_matches(limit=1, debug_html=True)
    out = capsys.readouterr().out
    assert "Debug HTML saved:" in out
    assert "PRIVATE_HTML_CONTENT" not in out
