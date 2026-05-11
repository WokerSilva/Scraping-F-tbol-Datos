from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def test_match_payload_allows_empty_stats_events():
    html = "<title>Estadísticas A vs B, Liga MX - Clausura Jornada 1</title><link rel=\"canonical\" href=\"https://es.besoccer.com/partido/a/b/20260001\"/>"
    m = MatchParser().parse_match(html, url="https://es.besoccer.com/partido/a/b/20260001", competition_slug="clausura_mexico")
    assert m.payload["stats_json"] == {}
    assert m.payload["events_json"] == []
