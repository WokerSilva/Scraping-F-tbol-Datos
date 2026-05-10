from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Any

from besoccer_scraper.shared.exceptions import HttpFetchError


@dataclass
class BrowserCompetitionRenderer:
    wait_after_load_ms: int = 1200
    user_agent: str | None = None
    round_selectors: tuple[str, ...] = (
        'select[data-cy="roundSelect"]',
        '.select-desktop select[onchange*="jsonMatches"]',
        '.select-mobile select[onchange*="jsonMatches"]',
        'select[onchange*="jsonMatches"]',
        'select[name="season"][data-cy="roundSelect"]',
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
        network_events: list[dict[str, Any]] = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=self.user_agent,
                locale="es-MX",
                timezone_id="America/Mexico_City",
                viewport={"width": 1440, "height": 2200},
                extra_http_headers={
                    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            page = context.new_page()
            page.on("response", lambda r: network_events.append({"url": r.url, "status": r.status, "method": r.request.method, "resource_type": r.request.resource_type}))
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            if response is None:
                debug = self._save_debug(page=page, competition=competition, year=year, requested_url=url, response=None, network_events=network_events)
                raise HttpFetchError(f"Navigation returned no response. Debug snapshot: {debug}", url=url)
            for state in ("load", "networkidle"):
                try:
                    page.wait_for_load_state(state, timeout=15_000)
                except PlaywrightTimeoutError:
                    pass
            self._wait_for_any(page, ('body', 'main', 'a[href*="/partido/"]', 'select[data-cy="roundSelect"]', 'select[onchange*="jsonMatches"]'))
            page.wait_for_timeout(max(self.wait_after_load_ms, 3500))
            if self._is_empty_render(page):
                debug = self._save_debug(page=page, competition=competition, year=year, requested_url=url, response=response, network_events=network_events)
                raise HttpFetchError(f"Rendered page is empty. Debug snapshot: {debug}", url=url)

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
                debug = self._save_debug(page=page, competition=competition, year=year, requested_url=url, response=response, network_events=network_events)
                body_len = len(self._body_text(page))
                raise HttpFetchError(f"No se pudo extraer página de competición. La página renderizada no contiene selector de jornadas ni partidos. Debug: {debug}. Status: {response.status}. Final URL: {page.url}. Body length: {body_len}", url=url)

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

    def _save_debug(self, *, page: object, competition: str | None, year: int | None, requested_url: str, response: object | None, network_events: list[dict[str, Any]]) -> str:
        base = Path("data/snapshots/errors")
        base.mkdir(parents=True, exist_ok=True)
        safe_competition = competition or "unknown_competition"
        safe_year = year if year is not None else "unknown_year"
        stem = f"mx_season_{safe_competition}_{safe_year}_failed"
        html_path = base / f"{stem}.html"
        png_path = base / f"{stem}.png"
        meta_path = base / f"{stem}_meta.json"
        html = page.content()
        body_text = self._body_text(page)
        html_path.write_text(html, encoding="utf-8")
        page.screenshot(path=str(png_path), full_page=True)
        has_round_select = page.locator('select[data-cy="roundSelect"]').count() > 0
        has_json_matches = page.locator('select[onchange*="jsonMatches"]').count() > 0
        anchors = page.locator('a[href*="/partido/"]').count()
        meta = {
            "requested_url": requested_url,
            "final_url": page.url,
            "title": page.title(),
            "response_status": getattr(response, "status", None),
            "response_url": getattr(response, "url", None),
            "response_headers": self._safe_headers(getattr(response, "headers", {})() if response else {}),
            "html_length": len(html),
            "body_text_length": len(body_text),
            "body_text_head": body_text[:1000],
            "has_round_select": has_round_select,
            "has_json_matches": has_json_matches,
            "match_anchor_count": anchors,
            "has_body_tag": "<body" in html.lower(),
            "has_main_tag": "<main" in html.lower(),
            "network_events": network_events[:30],
            "screenshot_path": str(png_path),
            "html_path": str(html_path),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(meta_path)

    @staticmethod
    def _safe_headers(headers: dict[str, str]) -> dict[str, str]:
        redacted = {"authorization", "cookie", "set-cookie"}
        return {k: ("<redacted>" if k.lower() in redacted else v) for k, v in headers.items()}

    @staticmethod
    def _body_text(page: object) -> str:
        try:
            return (page.locator("body").inner_text(timeout=2_000) or "").strip()
        except Exception:
            return ""

    def _is_empty_render(self, page: object) -> bool:
        html = page.content()
        title = (page.title() or "").strip()
        body_text = self._body_text(page)
        return not title and not body_text and len(html.strip()) < 200

    @staticmethod
    def _wait_for_any(page: object, selectors: tuple[str, ...]) -> None:
        for selector in selectors:
            try:
                page.wait_for_selector(selector, state="attached", timeout=2_500)
                return
            except Exception:
                continue

    @staticmethod
    def _dismiss_cookies(page: object) -> None:
        labels = ["Acepto", "Aceptar", "Accept", "Entendido", "OK"]
        for label in labels:
            button = page.get_by_role("button", name=label)
            if button.count() > 0:
                button.first.click(timeout=500)
                time.sleep(0.1)
                break
