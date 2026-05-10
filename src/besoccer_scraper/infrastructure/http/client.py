from __future__ import annotations

from dataclasses import dataclass
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from besoccer_scraper.shared.exceptions import HttpFetchError, ScrapeBlockedError

BLOCKED_STATUS_CODES = {403, 406, 429}


@dataclass
class HttpClient:
    timeout_seconds: float
    user_agent: str
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5

    def get(self, url: str) -> str:
        request = Request(url, headers=self._headers(), method="GET")
        attempt = 0
        while True:
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                    content = response.read().decode("utf-8", errors="ignore")
                    if self._looks_like_challenge(content):
                        raise ScrapeBlockedError("HTTP response looks like anti-bot challenge", status_code=response.status, url=url)
                    return content
            except HTTPError as exc:
                if exc.code in BLOCKED_STATUS_CODES:
                    raise ScrapeBlockedError(f"HTTP blocked request ({exc.code})", status_code=exc.code, url=url) from None
                raise HttpFetchError(f"HTTP fetch failed ({exc.code})", status_code=exc.code, url=url) from None
            except ScrapeBlockedError:
                raise
            except (TimeoutError, URLError):
                attempt += 1
                if attempt > self.max_retries:
                    raise HttpFetchError("HTTP fetch failed after retries", url=url) from None
                time.sleep(self.retry_backoff_seconds * attempt)

    def _headers(self) -> dict[str, str]:
        return {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }

    @staticmethod
    def _looks_like_challenge(content: str) -> bool:
        body = content.lower()
        return any(marker in body for marker in ("captcha", "cf-challenge", "cloudflare", "attention required"))
