from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def test_match_parser_cleanup_phase_fields_and_status_fin():
    html = '''
    <html><head>
    <title>Estadísticas Mazatlán vs FC Juárez, Liga MX - Clausura Jornada 1</title>
    <script type="application/ld+json">{"eventStatus":"https://schema.org/EventCompleted","description":"Mazatlán 1 - 2 FC Juárez"}</script>
    <script type="application/ld+json">{"location":{"name":"Estadio Mazatlán El Kraken"}}</script>
    <section id="events-goals">23' <a href="/jugador/1">Madson</a> gol 35' <a href="/jugador/2">Iván González</a> gol 47' <a href="/jugador/3">Puma Rodríguez</a> gol 47' <a href="/jugador/3">Puma Rodríguez</a> gol</section>
    <section id="mod_stats">
      <table>
        <tr><td>45%</td><td>Posesión</td><td>55%</td></tr>
        <tr><td>9</td><td>Remates</td><td>12</td></tr>
        <tr><td>4</td><td>Remates a puerta</td><td>6</td></tr>
        <tr><td>2</td><td>Corners</td><td>8</td></tr>
      </table>
    </section>
    </head></html>
    '''

    m = MatchParser().parse_match(
        html,
        url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018",
        competition_slug="clausura_mexico",
        round_label="JORNADA1",
        season_key="clausura-2026",
    )

    assert m.home_team == "Mazatlán"
    assert m.away_team == "FC Juárez"

    payload = m.payload
    assert payload["metadata"]["status"] == "FIN"
    assert payload["metadata"]["score"] == "1-2"
    assert payload["metadata"]["venue"] == "Estadio Mazatlán El Kraken"
    assert payload["round_label"] == "JORNADA1"
    assert payload["season_key"] == "clausura-2026"

    events = payload["events_json"]
    assert len(events) == 3
    assert [e["player_name"] for e in events] == ["Madson", "Iván González", "Puma Rodríguez"]

    stats = payload["stats_json"]
    assert stats["possession"] == {"home": "45%", "away": "55%"}
    assert stats["shots_total"] == {"home": "9", "away": "12"}
    assert stats["shots_on_target"] == {"home": "4", "away": "6"}
    assert stats["corners"] == {"home": "2", "away": "8"}


def test_goal_dedupe_uses_team_side_and_player_name_is_clean_text_only():
    payload = {
        "timeline": [
            {"type": "goal", "minute": "10", "player": "<a>A</a>", "team": "home"},
            {"type": "goal", "minute": "10", "player": "A", "team": "home"},
            {"type": "goal", "minute": "10", "player": "A", "team": "away"},
            {"type": "yellow_card", "minute": "11", "player": "No Goal"},
        ]
    }

    events = MatchParser()._extract_events(payload, "<html></html>")

    assert len(events) == 2
    assert {e["team_side"] for e in events} == {"home", "away"}
    assert all("<" not in (e["player_name"] or "") for e in events)
