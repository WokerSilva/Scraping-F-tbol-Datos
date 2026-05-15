from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def _fixture_html() -> str:
    return '''
    <html><head>
    <title>Estadísticas Mazatlán vs FC Juárez, Liga MX - Clausura Jornada 1</title>
    <script type="application/ld+json">{"eventStatus":"https://schema.org/EventCompleted","description":"Mazatlán 1 - 2 FC Juárez"}</script>
    <script type="application/ld+json">{"location":{"name":"Estadio Mazatlán El Kraken"}}</script>
    <section id="events-goals">
      <div class="table-played-match left">
        <span class="minute">23</span>
        <img alt="Gol" src="g.png"/>
        <a data-cy="event" href="/jugador/1">Madson</a>
        <a class="color-grey2" data-cy="event" href="/jugador/11">Asistencia X</a>
      </div>
      <div class="table-played-match right accion1">
        <span class="minute">35</span>
        <a data-cy="event" href="/jugador/2">Iván González</a>
      </div>
      <div class="table-played-match right">
        <span class="minute">45 +2</span>
        <img alt="Gol" src="g.png"/>
        <a data-cy="event" href="/jugador/3">Puma Rodríguez</a>
      </div>
    </section>
    <section id="events-changes">
      <div class="table-played-match"><img alt="Cambio"/><a data-cy="event">Sustituciones</a></div>
    </section>
    <section id="mod_stats">
      <table>
        <tr><td>45%</td><td>Posesión</td><td>55%</td></tr>
      </table>
    </section>
    </head></html>
    '''


def test_match_parser_maps_teams_to_columns():
    m = MatchParser().parse_match(
        _fixture_html(),
        url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018",
        competition_slug="clausura_mexico",
        round_label="JORNADA1",
        season_key="clausura-2026",
    )
    assert m.payload["home_team_name"] == "Mazatlán"
    assert m.payload["away_team_name"] == "FC Juárez"


def test_match_parser_goals_only_from_events_goals():
    events = MatchParser()._extract_events({}, _fixture_html())
    assert len(events) == 3
    assert all(e["event_type"] == "goal" for e in events)


def test_match_parser_goals_count_matches_score():
    m = MatchParser().parse_match(_fixture_html(), url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018", competition_slug="clausura_mexico", round_label="JORNADA1", season_key="clausura-2026")
    assert m.payload["metadata"]["score"] == "1-2"
    assert len(m.payload["events_json"]) == 3


def test_match_parser_player_name_clean():
    events = MatchParser()._extract_events({}, _fixture_html())
    for event in events:
        name = event["player_name"]
        assert name is not None
        assert "<div" not in name
        assert name != "+2"
        assert name != "Sustituciones"


def test_match_parser_stats_mod_stats():
    m = MatchParser().parse_match(_fixture_html(), url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018", competition_slug="clausura_mexico", round_label="JORNADA1", season_key="clausura-2026")
    assert m.payload["metadata"]["status"] == "FIN"
    assert m.payload["stats_json"]
    assert "possession" in m.payload["stats_json"]


def test_match_parser_added_time_minute_fields():
    events = MatchParser()._extract_events({}, _fixture_html())
    ev = events[-1]
    assert ev["minute"] == 45
    assert ev["minute_raw"] == "45+2"
    assert ev["added_time"] == 2
    assert ev["half"] == "first_half"


def test_match_parser_skips_empty_anchor_and_keeps_goal_player():
    html = """
    <section id="events-goals">
      <div class="table-played-match right">
        <span class="minute">35</span>
        <img alt="Gol" src="g.png"/>
        <a data-cy="event" href="/jugador/empty"></a>
        <a data-cy="event" href="/jugador/10">F. Almada</a>
        <a class="color-grey2" data-cy="event" href="/jugador/20">Iván González</a>
      </div>
    </section>
    """
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 1
    assert events[0]["player_name"] == "F. Almada"
    assert events[0]["assist_player_name"] == "Iván González"
