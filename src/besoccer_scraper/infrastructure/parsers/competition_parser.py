from __future__ import annotations

from besoccer_scraper.domain.entities import Competition


class CompetitionParser:
    def parse(self, html: str) -> list[Competition]:
        return [Competition(external_id="sample_comp", name="Sample League")]
