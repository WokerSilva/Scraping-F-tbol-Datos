from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import time
from typing import Any
from urllib.parse import urlparse

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

    def discover_rounds(
        self,
        *,
        url: str,
        competition: str | None = None,
        year: int | None = None,
    ) -> list[dict[str, object]]:
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception as exc:
            raise HttpFetchError("Playwright browser fallback is unavailable") from exc

        round_results: list[dict[str, object]] = []
        network_events: list[dict[str, Any]] = []
        blocked_external_navigation_count = 0
        blocked_domains_seen: list[str] = []
        external_navigation_events: list[str] = []
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
            def _route_handler(route: object) -> None:
                nonlocal blocked_external_navigation_count
                req = route.request
                host = self._hostname(req.url)
                rtype = req.resource_type
                if self._is_blocked_domain(host) or (rtype in {"image", "media", "font"} and not self._is_allowed_host(host)):
                    blocked_external_navigation_count += 1
                    blocked_domains_seen.append(host)
                    route.abort()
                    return
                if req.is_navigation_request() and not self._is_allowed_host(host):
                    blocked_external_navigation_count += 1
                    blocked_domains_seen.append(host)
                    route.abort()
                    return
                route.continue_()

            context.route("**/*", _route_handler)
            page = context.new_page()
            page.on("response", lambda r: network_events.append({"url": r.url, "status": r.status, "method": r.request.method, "resource_type": r.request.resource_type}))
            page.on("framenavigated", lambda frame: self._capture_external_navigation(frame.url, external_navigation_events))
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            if response is None:
                debug = self._save_debug(page=page, competition=competition, year=year, requested_url=url, response=None, network_events=network_events, blocked_external_navigation_count=blocked_external_navigation_count, blocked_domains=blocked_domains_seen)
                raise HttpFetchError(f"Navigation returned no response. Debug snapshot: {debug}", url=url)
            for state in ("load", "networkidle"):
                try:
                    page.wait_for_load_state(state, timeout=15_000)
                except PlaywrightTimeoutError:
                    pass
            self._wait_for_any(page, ('body', 'main', 'a[href*="/partido/"]', 'select[data-cy="roundSelect"]', 'select[onchange*="jsonMatches"]'))
            page.wait_for_timeout(max(self.wait_after_load_ms, 3500))
            if self._is_empty_render(page):
                debug = self._save_debug(page=page, competition=competition, year=year, requested_url=url, response=response, network_events=network_events, blocked_external_navigation_count=blocked_external_navigation_count, blocked_domains=blocked_domains_seen)
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
                dom = page.evaluate(
                    """() => {
                        const anchors = Array.from(document.querySelectorAll('a[href*="/partido/"]'));
                        const matches = anchors.map((a) => {
                            const href = a.getAttribute('href') || '';
                            const id = href.split('/').filter(Boolean).pop() || '';
                            return {url: href, source_match_id: id, scope_hint: 'main'};
                        });
                        return {matches, diagnostics: {match_anchor_count_global: anchors.length, match_anchor_count_scoped: anchors.length, scope_found: false}};
                    }"""
                )
                return [{"round_label": "JORNADA_ACTUAL", "matches": dom.get("matches", []), "diagnostics": dom.get("diagnostics", {})}]
            if not select_selector:
                debug = self._save_debug(page=page, competition=competition, year=year, requested_url=url, response=response, network_events=network_events, blocked_external_navigation_count=blocked_external_navigation_count, blocked_domains=blocked_domains_seen)
                body_len = len(self._body_text(page))
                raise HttpFetchError(f"No se pudo extraer página de competición. La página renderizada no contiene selector de jornadas ni partidos. Debug: {debug}. Status: {response.status}. Final URL: {page.url}. Body length: {body_len}", url=url)

            select = page.locator(select_selector)
            options = select.locator("option")
            count = options.count()
            for idx in range(count):
                option = options.nth(idx)
                value = (option.get_attribute("value") or "").strip()
                label = (option.inner_text() or "").strip() or f"round-{idx+1}"
                self._set_round_via_js(page=page, selector=select_selector, value=value, index=idx)
                page.wait_for_timeout(self.wait_after_load_ms)
                page.wait_for_selector('a[href*="/partido/"]', state="attached", timeout=5_000)
                dom = page.evaluate(
                    """() => {
                        const scope = document.querySelector('#mod_mainCompetitionRounds') || document.querySelector('.comp-matches') || document.querySelector('.panel-body.match-list-new') || document.querySelector('main');
                        const globalAnchors = Array.from(document.querySelectorAll('a[href*="/partido/"]'));
                        const scopedAnchors = scope ? Array.from(scope.querySelectorAll('a[href*="/partido/"]')) : [];
                        const matches = [];
                        const seen = new Set();
                        for (const a of scopedAnchors) {
                            const href = a.getAttribute('href') || '';
                            const id = href.split('/').filter(Boolean).pop() || '';
                            if (!href || seen.has(id)) continue;
                            seen.add(id);
                            matches.push({url: href, source_match_id: id, scope_hint: '#mod_mainCompetitionRounds'});
                        }
                        return {matches, diagnostics: {match_anchor_count_global: globalAnchors.length, match_anchor_count_scoped: scopedAnchors.length, scope_found: Boolean(scope)}};
                    }"""
                )
                round_results.append({"round_label": label, "matches": dom.get("matches", []), "diagnostics": dom.get("diagnostics", {})})

            context.close()
            browser.close()

        if not round_results:
            raise HttpFetchError("Browser fallback could not extract round pages", url=url)
        return round_results

    def render_round_pages(self, *, url: str, competition: str | None = None, year: int | None = None) -> list[tuple[str, str]]:
        rounds = self.discover_rounds(url=url, competition=competition, year=year)
        return [(str(r.get("round_label", "JORNADA")), "") for r in rounds]

    def _save_debug(self, *, page: object, competition: str | None, year: int | None, requested_url: str, response: object | None, network_events: list[dict[str, Any]], blocked_external_navigation_count: int, blocked_domains: list[str], external_navigation_events: list[str] | None = None) -> str:
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
            "blocked_external_navigation_count": blocked_external_navigation_count,
            "blocked_domains": blocked_domains,
            "external_navigation_events": external_navigation_events or [],
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

    def _is_allowed_host(self, host: str) -> bool:
        return any(host == item or host.endswith(f".{item}") for item in self.allowed_hosts)

    def _is_blocked_domain(self, host: str) -> bool:
        return any(host == item or host.endswith(f".{item}") for item in self.blocked_domains)

    @staticmethod
    def _hostname(url: str) -> str:
        return (urlparse(url).hostname or "").lower()

    def _raise_if_external_url(self, url: str) -> None:
        host = self._hostname(url)
        if host and not self._is_allowed_host(host):
            raise HttpFetchError(f"External navigation blocked/detected: {url}", url=url)

    def _capture_external_navigation(self, url: str, events: list[str]) -> None:
        host = self._hostname(url)
        if host and not self._is_allowed_host(host):
            events.append(url)

    @staticmethod
    def _extract_jsonmatches_args(onchange: str) -> list[int]:
        if "jsonMatches(" not in onchange:
            return []
        inside = onchange.split("jsonMatches(", 1)[1].split(")", 1)[0]
        values = [chunk.strip() for chunk in inside.split(",")]
        out: list[int] = []
        for item in values[1:]:
            try:
                out.append(int(item))
            except ValueError:
                continue
        return out

    def _set_round_via_js(self, *, page: object, selector: str, value: str, index: int) -> None:
        page.evaluate(
            """([selector, value, index]) => {
                const el = document.querySelector(selector);
                if (!el) return;
                if (value) { el.value = value; } else { el.selectedIndex = index; value = el.value; }
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                const onchange = String(el.getAttribute('onchange') || '');
                if (typeof window.jsonMatches === 'function') {
                    const match = onchange.match(/jsonMatches\\(this\\.value\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)\\s*\\)/);
                    if (match) { window.jsonMatches(value, Number(match[1]), Number(match[2]), Number(match[3])); }
                }
            }""",
            [selector, value, index],
        )

    @staticmethod
    def _dismiss_cookies(page: object) -> None:
        labels = ["Acepto", "Aceptar", "Accept", "Entendido", "OK", "Soy mayor de 18 años"]
        for label in labels:
            button = page.get_by_role("button", name=label)
            if button.count() > 0:
                button.first.click(timeout=500)
                time.sleep(0.1)
                break
    allowed_hosts: tuple[str, ...] = ("es.besoccer.com", "www.besoccer.com", "besoccer.com")
    blocked_domains: tuple[str, ...] = (
        "virushunterx.xyz", "doubleclick.net", "googlesyndication.com", "googleadservices.com",
        "fundingchoicesmessages.google.com", "ssm.codes", "scripts.ssm.codes", "smartclip-services.com",
        "adkaora.space", "teads.tv", "quantserve.com", "inmobi.com",
    )
