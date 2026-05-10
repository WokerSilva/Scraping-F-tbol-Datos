from __future__ import annotations


class HttpFetchError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, url: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class ScrapeBlockedError(HttpFetchError):
    """Raised when the source blocks basic HTTP scraping (403/406/429/challenge)."""
