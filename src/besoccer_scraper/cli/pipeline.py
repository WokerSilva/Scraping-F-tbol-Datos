from __future__ import annotations


def run_pipeline(container: object, discover_url: str, competition_id: str, scrape_url: str) -> dict[str, int | str]:
    return container.pipeline_use_case.execute(discover_url, competition_id, scrape_url)
