from __future__ import annotations

from dataclasses import dataclass
import time

from besoccer_scraper.shared.exceptions import HttpFetchError


@dataclass
class BrowserCompetitionRenderer:
    wait_after_load_ms: int = 1200

    def render_round_pages(self, *, url: str) -> list[tuple[str, str]]:
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
            try:
                page.wait_for_selector('select[data-cy="roundSelect"]', timeout=8_000)
            except PlaywrightTimeoutError as exc:
                raise HttpFetchError("Round selector not found in rendered competition page", url=url) from exc

            select = page.locator('select[data-cy="roundSelect"]')
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
                        ['select[data-cy="roundSelect"]', idx],
                    )
                page.wait_for_timeout(self.wait_after_load_ms)
                pages.append((label, page.content()))

            context.close()
            browser.close()

        if not pages:
            raise HttpFetchError("Browser fallback could not extract round pages", url=url)
        return pages

    @staticmethod
    def _dismiss_cookies(page: object) -> None:
        labels = ["Acepto", "Aceptar", "Accept", "Entendido", "OK"]
        for label in labels:
            button = page.get_by_role("button", name=label)
            if button.count() > 0:
                button.first.click(timeout=500)
                time.sleep(0.1)
                break
