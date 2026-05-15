from besoccer_scraper.application.scraping import ScrapeMatchesUseCase
from besoccer_scraper.cli.app import build_parser


def test_rescrape_command_exists():
    args = build_parser().parse_args([
        "scrape",
        "rescrape-matches",
        "--competition",
        "clausura_mexico",
        "--season-key",
        "clausura-2026",
        "--limit",
        "10",
    ])
    assert args.scrape_mode == "rescrape-matches"


class _Http:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return "<html></html>"


class _Parser:
    def parse_match(self, html, **kwargs):
        class M:
            external_id = "2026239018"
            payload = {
                "source_match_id": "2026239018",
                "competition_slug": "clausura_mexico",
                "round_label": kwargs.get("round_label"),
                "season_key": kwargs.get("season_key"),
                "metadata": {},
                "stats_json": {"a": 1, "b": 2},
                "events_json": [{"x": 1}, {"x": 2}, {"x": 3}],
            }

        return M()


class _MatchesRepo:
    def __init__(self, rows):
        self.rows = rows
        self.last_filters = None
        self.upserts = 0

    def list_matches_for_rescrape(self, **kwargs):
        self.last_filters = kwargs
        return self.rows

    def upsert_match(self, **kwargs):
        self.upserts += 1
        return 1


class _Uow:
    def __init__(self, rows):
        self.matches = _MatchesRepo(rows)
        self.raw_pages = type("RP", (), {"save_raw_page": lambda *a, **k: 77})()
        self.scrape_targets = object()
        self.job_runs = object()

    def commit(self):
        pass


def test_rescrape_lists_existing_matches():
    rows = [{"id": 1, "source_match_id": "2026239018", "url": "https://x", "source_competition_slug": "clausura_mexico", "season_key": "clausura-2026", "round_label": "J1"}]
    uow = _Uow(rows)
    uc = ScrapeMatchesUseCase(uow=uow, http_client=_Http(), parser=_Parser(), request_policy=None)
    uc.execute_rescrape_matches(competition_slug="clausura_mexico", season_key="clausura-2026", limit=10)
    assert uow.matches.last_filters == {
        "competition_slug": "clausura_mexico",
        "season_key": "clausura-2026",
        "limit": 10,
        "source_match_id": None,
    }


def test_rescrape_uses_existing_url_round_and_season():
    rows = [{"id": 1, "source_match_id": "2026239018", "url": "https://es.besoccer.com/partido/a/b/2026239018", "source_competition_slug": "clausura_mexico", "season_key": "clausura-2026", "round_label": "JORNADA7"}]
    http = _Http()
    uc = ScrapeMatchesUseCase(uow=_Uow(rows), http_client=http, parser=_Parser(), request_policy=None)
    out = uc.execute_rescrape_matches(competition_slug="clausura_mexico", season_key="clausura-2026")
    assert http.urls == ["https://es.besoccer.com/partido/a/b/2026239018"]
    assert out["matches_upserted"] == 1


class _HttpFailFirst(_Http):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def get(self, url):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("boom")
        return super().get(url)


def test_rescrape_continues_after_error():
    rows = [
        {"id": 1, "source_match_id": "1", "url": "https://x/1", "source_competition_slug": "clausura_mexico", "season_key": "clausura-2026", "round_label": "J1"},
        {"id": 2, "source_match_id": "2", "url": "https://x/2", "source_competition_slug": "clausura_mexico", "season_key": "clausura-2026", "round_label": "J2"},
    ]
    uow = _Uow(rows)
    out = ScrapeMatchesUseCase(uow=uow, http_client=_HttpFailFirst(), parser=_Parser(), request_policy=None).execute_rescrape_matches(
        competition_slug="clausura_mexico", season_key="clausura-2026"
    )
    assert out["failed"] == 1
    assert out["parsed"] == 1
    assert uow.matches.upserts == 1


def test_rescrape_summary_counts():
    rows = [
        {"id": 1, "source_match_id": "1", "url": "https://x/1", "source_competition_slug": "clausura_mexico", "season_key": "clausura-2026", "round_label": "J1"},
        {"id": 2, "source_match_id": "2", "url": "https://x/2", "source_competition_slug": "clausura_mexico", "season_key": "clausura-2026", "round_label": "J2"},
    ]
    uow = _Uow(rows)
    out = ScrapeMatchesUseCase(uow=uow, http_client=_Http(), parser=_Parser(), request_policy=None).execute_rescrape_matches(
        competition_slug="clausura_mexico", season_key="clausura-2026"
    )
    assert out["selected"] == 2
    assert out["parsed"] == 2
    assert out["failed"] == 0
    assert out["raw_pages_saved"] == 2
    assert out["matches_upserted"] == 2
    assert out["avg_stats_count"] == 2.0
    assert out["avg_events_count"] == 3.0
