from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HttpClient:
    timeout_seconds: float
    user_agent: str

    def get(self, url: str) -> str:
        return f"<html data-url='{url}'></html>"
