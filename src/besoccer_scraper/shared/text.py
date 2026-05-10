from __future__ import annotations

import re
from urllib.parse import urlparse


def extract_source_match_id(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    m = re.search(r"/(\d+)$", path)
    return m.group(1) if m else None
