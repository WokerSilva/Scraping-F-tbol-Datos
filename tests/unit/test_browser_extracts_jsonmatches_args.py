from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer


def test_extracts_jsonmatches_args() -> None:
    args = BrowserCompetitionRenderer._extract_jsonmatches_args("jsonMatches(this.value, 141, 1, 1)")
    assert args == [141, 1, 1]
