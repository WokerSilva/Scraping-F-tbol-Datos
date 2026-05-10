from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import TypedDict
from urllib.parse import urlparse

from bs4 import BeautifulSoup


_MATCH_PATH_RE = re.compile(r"^/partido/(?P<slug>[^/]+)/(?P<id>\d+)$", re.IGNORECASE)
_JSON_MATCHES_RE = re.compile(r"jsonMatches\((?P<args>[^)]*)\)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+")


class CompetitionMatchPayload(TypedDict):
    url: str
    source_match_id: str
    starttime: str | None
    home_team_name: str
    away_team_name: str
    score_status: str


class CompetitionPagePayload(TypedDict):
    competition_name: str
    available_rounds: list[str]
    selected_round: str | None
    matches: list[CompetitionMatchPayload]


@dataclass(frozen=True)
class ParsedCompetitionMatch:
    url: str
    source_match_id: str
    starttime: str | None
    home_team_name: str
    away_team_name: str
    score_status: str


@dataclass(frozen=True)
class ParsedCompetitionPage:
    competition_name: str
    available_rounds: list[str]
    selected_round: str | None
    matches: list[ParsedCompetitionMatch]

    def as_payload(self) -> CompetitionPagePayload:
        return {
            "competition_name": self.competition_name,
            "available_rounds": self.available_rounds,
            "selected_round": self.selected_round,
            "matches": [asdict(match) for match in self.matches],
        }


class CompetitionParser:
    def parse(self, html: str) -> CompetitionPagePayload:
        parsed = self.parse_rendered(html)
        return parsed.as_payload()

    def parse_rendered(self, html: str) -> ParsedCompetitionPage:
        soup = BeautifulSoup(html, "html.parser")
        competition_name = self._extract_competition_name(soup)
        available_rounds, selected_round = self._extract_rounds(soup)
        matches = self._extract_matches(soup)
        return ParsedCompetitionPage(
            competition_name=competition_name,
            available_rounds=available_rounds,
            selected_round=selected_round,
            matches=matches,
        )

    def _extract_competition_name(self, soup: BeautifulSoup) -> str:
        meta = soup.find("meta", attrs={"property": "og:title"})
        if meta and meta.get("content"):
            return str(meta.get("content")).strip()

        heading = soup.select_one("h1")
        if heading:
            text = heading.get_text(" ", strip=True)
            if text:
                return text

        title = soup.find("title")
        return title.get_text(" ", strip=True) if title else ""

    def _extract_rounds(self, soup: BeautifulSoup) -> tuple[list[str], str | None]:
        round_select = soup.select_one('select[data-cy="roundSelect"]')
        if round_select is None:
            round_select = self._select_with_jsonmatches_onchange(soup)

        if round_select is None:
            return self._extract_rounds_from_scripts(soup), None

        rounds: list[str] = []
        selected_round: str | None = None
        for option in round_select.select("option"):
            label = option.get_text(" ", strip=True)
            if not label:
                continue
            rounds.append(label)
            if option.has_attr("selected"):
                selected_round = label

        if selected_round is None and rounds:
            selected_index = round_select.get("selectedIndex")
            if isinstance(selected_index, str) and selected_index.isdigit():
                idx = int(selected_index)
                if 0 <= idx < len(rounds):
                    selected_round = rounds[idx]
        if selected_round is None and rounds:
            selected_round = rounds[0]
        return rounds, selected_round

    def _select_with_jsonmatches_onchange(self, soup: BeautifulSoup):
        for candidate in soup.select("select[onchange]"):
            onchange = str(candidate.get("onchange", ""))
            if _JSON_MATCHES_RE.search(onchange):
                return candidate
        return None

    def _extract_rounds_from_scripts(self, soup: BeautifulSoup) -> list[str]:
        rounds: list[str] = []
        for script in soup.find_all("script"):
            content = script.string or script.get_text(" ", strip=True)
            if "jsonMatches" not in content:
                continue
            for match in _JSON_MATCHES_RE.finditer(content):
                numbers = _NUMBER_RE.findall(match.group("args"))
                if numbers:
                    rounds.append(numbers[-1])
        # keep insertion order dedupe
        unique: list[str] = []
        seen: set[str] = set()
        for value in rounds:
            if value in seen:
                continue
            seen.add(value)
            unique.append(value)
        return unique

    def _extract_matches(self, soup: BeautifulSoup) -> list[ParsedCompetitionMatch]:
        parsed: list[ParsedCompetitionMatch] = []
        seen_ids: set[str] = set()

        for anchor in soup.select('a[href*="/partido/"]'):
            href = str(anchor.get("href", "")).strip()
            normalized = self._normalize_match_url(href)
            if normalized is None:
                continue

            source_match_id = normalized.rsplit("/", 1)[-1]
            if source_match_id in seen_ids:
                continue

            container = anchor.find_parent(["article", "li", "tr", "div"]) or anchor
            home, away = self._extract_teams(container)
            status = self._extract_status(container)
            starttime = self._extract_starttime(container)

            parsed.append(
                ParsedCompetitionMatch(
                    url=normalized,
                    source_match_id=source_match_id,
                    starttime=starttime,
                    home_team_name=home,
                    away_team_name=away,
                    score_status=status,
                )
            )
            seen_ids.add(source_match_id)

        return parsed

    def _normalize_match_url(self, href: str) -> str | None:
        path = urlparse(href).path.strip()
        matched = _MATCH_PATH_RE.match(path)
        if not matched:
            return None
        return f"/partido/{matched.group('slug')}/{matched.group('id')}"

    def _extract_starttime(self, container) -> str | None:
        with_time = container.select_one("[data-starttime]")
        if with_time and with_time.get("data-starttime"):
            return str(with_time.get("data-starttime")).strip()

        time_tag = container.select_one("time")
        if time_tag:
            return str(time_tag.get("datetime") or time_tag.get_text(" ", strip=True) or "").strip() or None

        return None

    def _extract_teams(self, container) -> tuple[str, str]:
        home = self._text_first(container, [
            '[data-cy="homeTeam"]',
            ".team-home",
            ".home-team",
            ".local",
        ])
        away = self._text_first(container, [
            '[data-cy="awayTeam"]',
            ".team-away",
            ".away-team",
            ".visitor",
        ])

        if home and away:
            return home, away

        teams = [node.get_text(" ", strip=True) for node in container.select(".team-name, .name") if node.get_text(" ", strip=True)]
        if len(teams) >= 2:
            return teams[0], teams[1]
        return home or "", away or ""

    def _extract_status(self, container) -> str:
        status = self._text_first(container, [
            '[data-cy="matchStatus"]',
            ".marker",
            ".result",
            ".match-status",
            ".status",
            ".score",
        ])
        return status or ""

    @staticmethod
    def _text_first(container, selectors: list[str]) -> str:
        for selector in selectors:
            node = container.select_one(selector)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        return ""
