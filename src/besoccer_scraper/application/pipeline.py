from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PipelineUseCase:
    discover_uc: object
    scrape_uc: object
    audit_uc: object

    def execute(self, discover_url: str, competition_id: str, scrape_url: str) -> dict[str, int | str]:
        discovered = self.discover_uc.execute(discover_url)
        scraped = self.scrape_uc.execute(competition_id, scrape_url)
        run_id = self.audit_uc.execute(
            f"Pipeline completed with discovered={discovered} and scraped={scraped}"
        )
        return {"discovered": discovered, "scraped": scraped, "run_id": run_id}
