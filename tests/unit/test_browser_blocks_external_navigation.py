import pytest

from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer
from besoccer_scraper.shared.exceptions import HttpFetchError


def test_blocks_external_navigation_detection() -> None:
    with pytest.raises(HttpFetchError):
        BrowserCompetitionRenderer()._raise_if_external_url("https://virushunterx.xyz/path")
