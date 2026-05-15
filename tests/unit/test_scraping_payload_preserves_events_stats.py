from besoccer_scraper.application.scraping import ScrapeMatchesUseCase
from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


HTML = """
<html><head>
<title>Estadísticas Mazatlán vs FC Juárez, Liga MX - Clausura Jornada 1</title>
<script type="application/ld+json">{"eventStatus":"https://schema.org/EventCompleted","description":"Mazatlán 1 - 2 FC Juárez"}</script>
<section id="events-goals">
  <div class="table-played-match right visitor"><span class="min">23'</span><img alt="Gol"/><a data-cy="event">Francisco Nevarez</a><a data-cy="event">Madson</a><a data-cy="event"></a></div>
  <div class="table-played-match left local"><span class="min">35'</span><img src="/img/accion1.png"/><a data-cy="event"></a><a data-cy="event">F. Almada</a><a data-cy="event">Iván González</a></div>
  <div class="table-played-match right visitor"><span class="min">45'+2</span><div class="event-1"></div><a data-cy="event">Denzell García</a><a data-cy="event">Puma Rodríguez</a><a data-cy="event"></a></div>
</section>
<section id="mod_stats"><table><tr><td>45%</td><td>Posesión</td><td>55%</td></tr></table></section>
</head></html>
"""


class Http:
    def get(self, url):
        return HTML


class Matches:
    def __init__(self):
        self.payload = None

    def upsert_match(self, **kwargs):
        self.payload = kwargs["payload"]
        return 1


class U:
    def __init__(self):
        self.matches = Matches()
        self.raw_pages = type("RP", (), {"save_raw_page": lambda *a, **k: 3})()
        self.job_runs = type("R", (), {"start_run": lambda *a, **k: 1, "log_event": lambda *a, **k: None, "finish_run": lambda *a, **k: None})()
        self.scrape_targets = type("S", (), {"mark_transition": lambda *a, **k: True})()

    def commit(self):
        pass


def test_scraping_payload_preserves_events_stats():
    u = U()
    uc = ScrapeMatchesUseCase(uow=u, http_client=Http(), parser=MatchParser(), request_policy=None)
    uc.execute_match_url(url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018", competition_slug="clausura_mexico", round_label="JORNADA1", season_key="clausura-2026")
    assert len(u.matches.payload["events_json"]) == 3
    assert u.matches.payload["stats_json"]
