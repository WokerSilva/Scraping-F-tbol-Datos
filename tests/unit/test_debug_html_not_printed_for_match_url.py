from besoccer_scraper.application.scraping import ScrapeMatchesUseCase


class Http:
    def get(self, url): return "<html><body>SECRET_BLOCK</body></html>"

class Parser:
    def parse_match(self, html, **kwargs):
        class M:
            payload = {"source_match_id": "2026239018", "competition_slug": "clausura_mexico", "round_label": "JORNADA1", "metadata": {"score": "1-2"}, "stats_json": {}, "events_json": []}
        return M()

class U:
    class R:
        def start_run(self, **kwargs): return 1
        def log_event(self, **kwargs): pass
        def finish_run(self, **kwargs): pass
    class M:
        def upsert_many(self, matches): return 1
    class RP:
        def save_raw_page(self, **kwargs): return 9
    job_runs = R(); matches = M(); raw_pages = RP(); scrape_targets = type("S", (), {"mark_transition": lambda *a, **k: True})()
    def commit(self): pass


def test_debug_html_not_printed_for_match_url(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    ScrapeMatchesUseCase(uow=U(), http_client=Http(), parser=Parser(), request_policy=None).execute_match_url(url="https://es.besoccer.com/partido/a/b/2026239018", competition_slug="clausura_mexico", round_label="JORNADA1", debug_html=True)
    out = capsys.readouterr().out
    assert "Debug HTML saved:" in out
    assert "SECRET_BLOCK" not in out
