from besoccer_scraper.infrastructure.parsers.competition_parser import CompetitionParser


def test_competition_parser_excludes_global_search_matches() -> None:
    html = '''<html><body>
    <header><a href="/partido/foo/bar/2026000001">bad</a></header>
    <div class="comp-matches"><a data-cy="match" href="/partido/america/tigres/2026000002"></a><div class="middle-info">Liga MX - Clausura</div></div>
    </body></html>'''
    out = CompetitionParser().parse(html)
    ids = [m["source_match_id"] for m in out["matches"]]
    assert ids == ["2026000002"]
