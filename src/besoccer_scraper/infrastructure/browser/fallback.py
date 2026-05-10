from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time

from besoccer_scraper.shared.exceptions import HttpFetchError


@dataclass
class BrowserCompetitionRenderer:
    wait_after_load_ms: int = 1200
    round_selectors: tuple[str, ...] = (
        'select[data-cy="roundSelect"]',
        '.select-desktop select[onchange*="jsonMatches"]',
        '.select-mobile select[onchange*="jsonMatches"]',
        'select[onchange*="jsonMatches"]',
    )

    def render_round_pages(
        self,
        *,
        url: str,
        competition: str | None = None,
        year: int | None = None,
    ) -> list[tuple[str, str]]:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise HttpFetchError("Playwright browser fallback is unavailable") from exc

        pages: list[tuple[str, str]] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            self._dismiss_cookies(page)
            select_selector = None
            for selector in self.round_selectors:
                try:
                    page.wait_for_selector(selector, state="attached", timeout=2_500)
                    select_selector = selector
                    break
                except PlaywrightTimeoutError:
                    continue
            has_anchors = page.locator('a[href*="/partido/"]').count() > 0
            if not select_selector and has_anchors:
                return [("JORNADA_ACTUAL", page.content())]
            if not select_selector:
                debug = self._save_debug(page=page, competition=competition, year=year)
                raise HttpFetchError(f"Round selector not found. Debug snapshot: {debug}", url=url)

            select = page.locator(select_selector)
            options = select.locator("option")
            count = options.count()
            for idx in range(count):
                option = options.nth(idx)
                value = (option.get_attribute("value") or "").strip()
                label = (option.inner_text() or "").strip() or f"round-{idx+1}"
                if value:
                    select.select_option(value=value)
                else:
                    page.evaluate(
                        """([selector, index]) => {
                            const el = document.querySelector(selector);
                            if (!el) return;
                            el.selectedIndex = index;
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                            el.dispatchEvent(new Event('change', { bubbles: true }));
                        }""",
                        [select_selector, idx],
                    )
                page.wait_for_timeout(self.wait_after_load_ms)
                page.wait_for_selector('a[href*="/partido/"]', state="attached", timeout=5_000)
                pages.append((label, page.content()))

            context.close()
            browser.close()

        if not pages:
            raise HttpFetchError("Browser fallback could not extract round pages", url=url)
        return pages

    def _save_debug(self, *, page: object, competition: str | None, year: int | None) -> str:
        base = Path("data/snapshots/errors")
        base.mkdir(parents=True, exist_ok=True)
        safe_competition = competition or "unknown_competition"
        safe_year = year if year is not None else "unknown_year"
        stem = f"mx_season_{safe_competition}_{safe_year}_failed"
        html_path = base / f"{stem}.html"
        png_path = base / f"{stem}.png"
        meta_path = base / f"{stem}_meta.json"
        html_path.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(png_path), full_page=True)
        body_text = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
        meta_path.write_text(json.dumps({"title": page.title(), "url": page.url, "body_text_head": body_text[:1000]}, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(meta_path)

    @staticmethod
    def _dismiss_cookies(page: object) -> None:
        labels = ["Acepto", "Aceptar", "Accept", "Entendido", "OK"]
        for label in labels:
            button = page.get_by_role("button", name=label)
            if button.count() > 0:
                button.first.click(timeout=500)
                time.sleep(0.1)
                break
