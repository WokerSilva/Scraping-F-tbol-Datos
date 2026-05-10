from __future__ import annotations

from dataclasses import dataclass
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


@dataclass
class HttpClient:
    timeout_seconds: float
    user_agent: str
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5

    def get(self, url: str) -> str:
        request = Request(url, headers={"User-Agent": self.user_agent}, method="GET")
        attempt = 0
        while True:
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                    return response.read().decode("utf-8", errors="ignore")
            except (TimeoutError, URLError):
                attempt += 1
                if attempt > self.max_retries:
                    raise
                time.sleep(self.retry_backoff_seconds * attempt)
