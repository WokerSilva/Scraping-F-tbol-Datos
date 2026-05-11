from besoccer_scraper.infrastructure.browser.dom_extractors import extract_competition_matches_from_html


def test_extracts_only_scoped_matches() -> None:
    html = '''
    <header><a href="/partido/x/y/999">bad</a></header>
    <div class="autocomplete-box"><a href="/partido/x/y/998">bad2</a></div>
    <div id="mod_mainCompetitionRounds">
      <a href="/partido/club-a/club-b/2026239001">ok1</a>
      <a href="/partido/club-c/club-d/2026239002">ok2</a>
    </div>
    '''
    payload = extract_competition_matches_from_html(html)
    ids = [m["source_match_id"] for m in payload["matches"]]
    assert ids == ["2026239001", "2026239002"]
