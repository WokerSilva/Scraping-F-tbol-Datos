from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer


def test_browser_selector_fallbacks_include_expected_selectors() -> None:
    selectors = BrowserCompetitionRenderer().round_selectors
    assert 'select[data-cy="roundSelect"]' in selectors
    assert any('jsonMatches' in selector for selector in selectors)
