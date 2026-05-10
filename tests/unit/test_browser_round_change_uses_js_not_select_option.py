from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer


class _Page:
    def __init__(self):
        self.called = False

    def evaluate(self, script, params):
        self.called = True


def test_round_change_uses_js() -> None:
    page = _Page()
    BrowserCompetitionRenderer()._set_round_via_js(page=page, selector='select[data-cy="roundSelect"]', value="17", index=0)
    assert page.called is True
