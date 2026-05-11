from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def test_match_parser_minimal_snapshot():
    html = '''
    <html><head>
    <title>Estadísticas Mazatlán vs FC Juárez, Liga MX - Clausura Jornada 1</title>
    <link rel="canonical" href="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018"/>
    <script type="application/ld+json">{"description":"Mazatlán 1 - 2 FC Juárez"}</script>
    </head></html>
    '''
    m = MatchParser().parse_match(html, url="https://es.besoccer.com/partido/mazatlan-fc/fc-juarez/2026239018", competition_slug="clausura_mexico")
    p = m.payload
    assert p["source_match_id"] == "2026239018"
    assert m.home_team == "Mazatlán"
    assert m.away_team == "FC Juárez"
    assert p["metadata"]["score"] == "1-2"
    assert p["metadata"]["competition_name"] == "Liga MX - Clausura"
    assert p["metadata"]["round_label"] == "JORNADA1"
