from pathlib import Path
import pytest
try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def _snapshot_html() -> str:
    path = Path("data/snapshots/match_pages/match_2026239018.html")
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _fixture_html() -> str:
    return '''
    <html><head>
    <title>Estadísticas Mazatlán vs FC Juárez, Liga MX - Clausura Jornada 1</title>
    <script type="application/ld+json">{"eventStatus":"https://schema.org/EventCompleted","description":"Mazatlán 1 - 2 FC Juárez"}</script>
    <script type="application/ld+json">{"location":{"name":"Estadio Mazatlán El Kraken"}}</script>
    </head><body>
    <section id="events-goals">
      <div class="table-played-match left">
        <span class="min">23</span>
        <img alt="Gol" src="g.png"/>
        <a data-cy="event" href="/jugador/1">Madson</a>
      </div>
      <div class="table-played-match right accion1">
        <span class="min">35</span>
        <img src="/img/accion1.svg"/>
        <a data-cy="event" href="/jugador/2">Iván González</a>
      </div>
      <div class="table-played-match right">
        <span class="min">45 +2</span>
        <div class="event-1"><a class="main-text" data-cy="event" href="/jugador/3">Puma Rodríguez</a></div>
      </div>
    </section>
    <section id="events-changes">
      <div class="table-played-match"><img alt="Cambio"/><a data-cy="event">Sustituciones</a></div>
    </section>
    <section id="mod_stats">
      <div>45% Posesión 55%</div>
      <div>12 Remates 8</div>
    </section>
    </body></html>
    '''

def _fixture_html_real_rows() -> str:
    return """
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

def test_match_parser_snapshot_has_expected_selectors():
    html = _snapshot_html()
    if not html:
        return
    events_goals_found = 'id="events-goals"' in html
    goal_rows = html.count("table-played-match")
    goal_imgs = html.count('alt="Gol"')
    accion1_imgs = html.count("accion1")
    event1_nodes = html.count("event-1")
    mod_stats_found = 'id="mod_stats"' in html
    stats_text_has_posesion = "Posesión" in html
    assert events_goals_found
    assert goal_rows > 0
    assert goal_imgs > 0 or accion1_imgs > 0 or event1_nodes > 0
    assert mod_stats_found
    assert stats_text_has_posesion


def test_match_parser_extracts_3_goals_only_from_events_goals():
    events = MatchParser()._extract_events({}, _fixture_html())
    assert len(events) == 3


def test_match_parser_does_not_extract_substitutions_as_goals():
    events = MatchParser()._extract_events({}, _fixture_html())
    assert all(e["player_name"] != "Sustituciones" for e in events)


def test_match_parser_player_name_clean():
    events = MatchParser()._extract_events({}, _fixture_html())
    for event in events:
        name = event["player_name"]
        assert name is not None
        assert "<" not in name
        assert "</" not in name


def test_match_parser_added_time_not_as_player():
    events = MatchParser()._extract_events({}, _fixture_html())
    assert all(e["player_name"] != "+2" for e in events)
    added = [e for e in events if e["minute_raw"] == "45+2"]
    assert added and added[0]["minute"] == 45 and added[0]["added_time"] == 2


def test_match_parser_mod_stats_non_empty():
    m = MatchParser().parse_match(_fixture_html(), url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018", competition_slug="clausura_mexico", round_label="JORNADA1", season_key="clausura-2026")
    assert m.payload["stats_json"]


def test_match_parser_keeps_metadata_basic():
    m = MatchParser().parse_match(_fixture_html(), url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018", competition_slug="clausura_mexico", round_label="JORNADA1", season_key="clausura-2026")
    meta = m.payload["metadata"]
    assert m.payload["home_team_name"] == "Mazatlán"
    assert m.payload["away_team_name"] == "FC Juárez"
    assert meta["score"] == "1-2"
    assert meta["status"] == "FIN"
    assert meta["venue"] == "Estadio Mazatlán El Kraken"


@pytest.mark.skipif(BeautifulSoup is None, reason="bs4 not installed")
def test_match_parser_contract_real_like_snapshot_counts():
    html = _snapshot_html() or _fixture_html()
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one("#events-goals")
    assert len(soup.select("#events-goals .table-played-match")) >= 3
    assert soup.select_one("#mod_stats")
    m = MatchParser().parse_match(
        html,
        url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018",
        competition_slug="clausura_mexico",
        round_label="JORNADA1",
        season_key="clausura-2026",
    )
    assert len(m.payload["events_json"]) == 3
    assert len(m.payload["stats_json"]) > 0
    assert m.payload["home_team_name"] == "Mazatlán"
    assert m.payload["away_team_name"] == "FC Juárez"
    assert m.payload["metadata"]["status"] == "FIN"
    assert "parser_debug_counts" in m.payload["metadata"]


def test_match_parser_public_parse_real_snapshot_goals():
    m = MatchParser().parse_match(
        _fixture_html_real_rows(),
        url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018",
        competition_slug="clausura_mexico",
        round_label="JORNADA1",
        season_key="clausura-2026",
    )
    assert len(m.payload["events_json"]) == 3
    assert [e["player_name"] for e in m.payload["events_json"]] == ["Francisco Nevarez", "F. Almada", "Denzell García"]
    assert [e.get("assist_player_name") for e in m.payload["events_json"]] == ["Madson", "Iván González", "Puma Rodríguez"]


def test_match_parser_public_parse_real_snapshot_stats():
    m = MatchParser().parse_match(
        _fixture_html_real_rows(),
        url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018",
        competition_slug="clausura_mexico",
        round_label="JORNADA1",
        season_key="clausura-2026",
    )
    assert m.payload["stats_json"]
    counts = m.payload["metadata"]["parser_debug_counts"]
    assert counts["events_goals_found"] is True
    assert counts["goal_rows_found"] == 3
    assert counts["mod_stats_found"] is True
    assert counts["stats_text_has_posesion"] is True
