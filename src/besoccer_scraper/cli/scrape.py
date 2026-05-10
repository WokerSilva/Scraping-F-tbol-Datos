from __future__ import annotations


def run_scrape(container: object, competition_id: str, source_url: str) -> int:
    return container.scrape_use_case.execute(competition_id, source_url)
