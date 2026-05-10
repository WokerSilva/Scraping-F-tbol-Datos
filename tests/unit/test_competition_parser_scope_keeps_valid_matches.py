from besoccer_scraper.infrastructure.parsers.competition_parser import CompetitionParser


def test_competition_parser_scope_keeps_valid_matches() -> None:
    rows = "".join(
        f'<a data-cy="match" href="/partido/a/b/20260000{i:02d}">m{i}</a>'
        for i in range(1, 10)
    )
    html = f"""
    <html><head><title>Liga MX - Clausura</title></head><body>
      <header><a href=\"/partido/x/y/999999999\">bad</a></header>
      <div id=\"mod_mainCompetitionRounds\">{rows}</div>
      <div class=\"autocomplete-box\"><a href=\"/partido/x/y/888888888\">bad2</a></div>
    </body></html>
    """
    parsed = CompetitionParser().parse(html)
    assert len(parsed["matches"]) == 9
    ids = {m["source_match_id"] for m in parsed["matches"]}
    assert "999999999" not in ids
    assert "888888888" not in ids
