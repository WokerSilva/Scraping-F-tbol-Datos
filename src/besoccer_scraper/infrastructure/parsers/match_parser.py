from __future__ import annotations

import re
from datetime import datetime

from besoccer_scraper.domain.entities import Match


class MatchParser:
    _ID_PATTERNS = (
        re.compile(r"/partido/[^/]+/(?P<id>\d+)", re.IGNORECASE),
        re.compile(r'"matchId"\s*:\s*"?(?P<id>\d+)"?', re.IGNORECASE),
    )
    _TITLE_RE = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)
    _KICKOFF_RE = re.compile(r'"startDate"\s*:\s*"(?P<kickoff>[^"]+)"', re.IGNORECASE)

    def parse_match(
        self,
        html: str,
        *,
        url: str,
        competition_slug: str,
        round_label: str | None = None,
        season_key: str | None = None,
    ) -> Match:
        source_match_id = self._extract_match_id(url=url, html=html)
        home_team, away_team = self._extract_teams(html)
        kickoff_at = self._extract_kickoff(html)
        return Match(
            external_id=source_match_id,
            competition_id=competition_slug,
            home_team=home_team,
            away_team=away_team,
            kickoff_at=kickoff_at,
            payload={
                "source_match_id": source_match_id,
                "url": url,
                "competition_slug": competition_slug,
                "round_label": round_label,
                "season_key": season_key,
            },
        )

    def _extract_match_id(self, *, url: str, html: str) -> str:
        for pattern in self._ID_PATTERNS:
            matched = pattern.search(url) or pattern.search(html)
            if matched:
                return matched.group("id")
        raise ValueError("Unable to extract match id from URL/HTML")

    def _extract_teams(self, html: str) -> tuple[str, str]:
        title_match = self._TITLE_RE.search(html)
        if not title_match:
            return "", ""
        title = re.sub(r"\s+", " ", title_match.group("title")).strip()
        head = title.split("|")[0].strip()
        for separator in (" - ", " vs ", " vs. "):
            if separator in head:
                left, right = head.split(separator, 1)
                return left.strip(), right.strip()
        return "", ""

    def _extract_kickoff(self, html: str) -> datetime | None:
        kickoff_match = self._KICKOFF_RE.search(html)
        if not kickoff_match:
            return None
        raw = kickoff_match.group("kickoff").replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None
