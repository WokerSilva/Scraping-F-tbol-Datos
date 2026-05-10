import json
from pathlib import Path

from besoccer_scraper.infrastructure.browser.fallback import BrowserCompetitionRenderer


class _Locator:
    def __init__(self, text: str = "", count: int = 0):
        self._text = text
        self._count = count

    def inner_text(self, timeout: int = 0) -> str:
        return self._text

    def count(self) -> int:
        return self._count


class _Page:
    url = "https://example.test"

    def content(self) -> str:
        return "<html><body></body></html>"

    def title(self) -> str:
        return ""

    def locator(self, selector: str):
        if selector == "body":
            return _Locator(text="", count=1)
        return _Locator(text="", count=0)

    def screenshot(self, path: str, full_page: bool = True) -> None:
        Path(path).write_bytes(b"png")


def test_browser_empty_render_diagnosis(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    renderer = BrowserCompetitionRenderer()
    page = _Page()

    assert renderer._is_empty_render(page) is True
    meta_path = renderer._save_debug(
        page=page,
        competition="clausura_mexico",
        year=2026,
        requested_url="https://example.test",
        response=None,
        network_events=[],
        blocked_external_navigation_count=0,
        blocked_domains=[],
    )
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    assert meta["html_length"] > 0
    assert meta["body_text_length"] == 0
    assert meta["blocked_external_navigation_count"] == 0
    assert meta["blocked_domains"] == []

    message = f"Rendered page is empty. Debug snapshot: {meta_path}"
    assert "Rendered page is empty" in message
    assert "Round selector not found" not in message
