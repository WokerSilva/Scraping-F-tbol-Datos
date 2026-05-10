from __future__ import annotations


def run_discover(container: object, source_url: str) -> int:
    return container.discover_use_case.execute(source_url)
