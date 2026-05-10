from __future__ import annotations

import re

from besoccer_scraper.domain.entities import Match


_MATCH_LINK_RE = re.compile(r'href=["\'](?P<href>/partido/[^"\']*/(?P<id>\d+))["\']', re.IGNORECASE)


class TeamMatchesParser:
    def parse(self, html: str, competition_id: str) -> list[Match]:
        matches: list[Match] = []
        for found in _MATCH_LINK_RE.finditer(html):
            source_match_id = found.group("id")
            href = found.group("href")
            matches.append(
                Match(
                    external_id=source_match_id,
                    competition_id=competition_id,
                    home_team="",
                    away_team="",
                    payload={
                        "source_match_id": source_match_id,
                        "relative_url": href,
                    },
                )
            )
        return matches
