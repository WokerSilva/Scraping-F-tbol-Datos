from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer


def test_external_navigation_capture_no_throw() -> None:
    events = []
    BrowserCompetitionRenderer()._capture_external_navigation("https://chrome-error://chromewebdata/", events)
    assert isinstance(events, list)
    BrowserCompetitionRenderer()._capture_external_navigation("https://virushunterx.xyz/x", events)
    assert events
