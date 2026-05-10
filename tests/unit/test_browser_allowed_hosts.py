from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer


def test_browser_allowed_and_blocked_hosts() -> None:
    r = BrowserCompetitionRenderer()
    assert r._is_allowed_host("es.besoccer.com")
    assert not r._is_allowed_host("virushunterx.xyz")
    assert r._is_blocked_domain("doubleclick.net")
