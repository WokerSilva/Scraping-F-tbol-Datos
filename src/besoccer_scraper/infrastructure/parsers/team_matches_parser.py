from __future__ import annotations

from besoccer_scraper.domain.entities import Match


class TeamMatchesParser:
    def parse(self, html: str, competition_id: str) -> list[Match]:
        return [
            Match(
                external_id="sample_match",
                competition_id=competition_id,
                home_team="Home",
                away_team="Away",
            )
        ]
