from besoccer_scraper.infrastructure.browser.dom_extractors import extract_competition_matches_from_html


def test_detects_17_round_options() -> None:
    options = ''.join([f'<option value="{i}">Jornada {i}</option>' for i in range(1, 18)])
    html = f'<select data-cy="roundSelect">{options}</select>'
    payload = extract_competition_matches_from_html(html)
    assert len(payload["round_options"]) == 17
