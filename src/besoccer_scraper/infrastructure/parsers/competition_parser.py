from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from typing import TypedDict
from urllib.parse import urlparse

from bs4 import BeautifulSoup


_MATCH_PATH_RE = re.compile(r"/partido/.+?/(?P<id>\d{6,})(?:/)?$", re.IGNORECASE)
_MATCH_ID_FROM_ANCHOR_RE = re.compile(r"^match-(?P<id>\d{6,})$", re.IGNORECASE)
_JSON_MATCHES_RE = re.compile(r"jsonMatches\((?P<args>[^)]*)\)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+")
_ROUND_NUMBER_RE = re.compile(r"(\d+)")


class CompetitionMatchPayload(TypedDict):
    url: str
    source_match_id: str
    round_label: str | None
    starttime: str | None
    home_team_name: str
    away_team_name: str
    home_score: int | None
    away_score: int | None
    status: str
    competition_name: str
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
    round_label: str | None
    starttime: str | None
    home_team_name: str
    away_team_name: str
    home_score: int | None
    away_score: int | None
    status: str
    competition_name: str
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
        matches = self._extract_matches(soup, selected_round, competition_name)
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
            normalized = self._normalize_round_label(label)
            rounds.append(normalized or label)
            if option.has_attr("selected"):
                selected_round = normalized or label

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

    def _extract_matches(self, soup: BeautifulSoup, selected_round: str | None, competition_name: str) -> list[ParsedCompetitionMatch]:
        parsed: list[ParsedCompetitionMatch] = []
        seen_ids: set[str] = set()
        debug_enabled = os.getenv("BESOCCER_PARSER_DEBUG", "").lower() in {"1", "true", "yes"}

        containers = ["#mod_mainCompetitionRounds", ".comp-matches", ".panel-body.match-list-new"]
        selector_parts = [
            'a[data-cy="match"][href*="/partido/"]',
            'a[id^="match-"][href*="/partido/"]',
            'a.match-link[href*="/partido/"]',
        ]
        selectors = [f"{container} {part}" for container in containers for part in selector_parts]
        candidate_anchors = soup.select(",".join(selectors))
        if debug_enabled:
            total_partido = len(soup.select('a[href*="/partido/"]'))
            data_cy_match = len(soup.select('a[data-cy="match"]'))
            print(f"[competition_parser] anchors href*=/partido/: {total_partido}")
            print(f"[competition_parser] anchors data-cy=match: {data_cy_match}")
            print(f"[competition_parser] candidate anchors: {len(candidate_anchors)}")

        for anchor in candidate_anchors:
            href = str(anchor.get("href", "")).strip()
            normalized = self._normalize_match_url(href)
            if normalized is None:
                continue

            source_match_id = self._extract_source_match_id(normalized, anchor)
            if source_match_id is None:
                continue
            if source_match_id in seen_ids:
                continue

            container = anchor.find_parent(["article", "li", "tr", "div"]) or anchor
            home, away = self._extract_teams(container)
            home_score, away_score = self._extract_scores(container)
            status = self._extract_status(container)
            starttime = self._extract_starttime(container)
            match_competition_name = self._text_first(container, [".middle-info"]) or competition_name

            parsed.append(
                ParsedCompetitionMatch(
                    url=normalized,
                    source_match_id=source_match_id,
                    round_label=selected_round,
                    starttime=starttime,
                    home_team_name=home,
                    away_team_name=away,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    competition_name=match_competition_name,
                    score_status=status,
                )
            )
            seen_ids.add(source_match_id)

        if debug_enabled:
            print(f"[competition_parser] parsed matches: {len(parsed)}")
        return parsed

    @staticmethod
    def _normalize_round_label(label: str) -> str:
        text = (label or "").strip().upper()
        match = _ROUND_NUMBER_RE.search(text)
        if match:
            return f"JORNADA{int(match.group(1))}"
        return text

    def _normalize_match_url(self, href: str) -> str | None:
        path = urlparse(href).path.strip()
        matched = _MATCH_PATH_RE.match(path)
        if not matched:
            return None
        return f"https://es.besoccer.com{path.rstrip('/')}"

    def _extract_source_match_id(self, normalized_url: str, anchor) -> str | None:
        matched = _MATCH_PATH_RE.search(urlparse(normalized_url).path)
        if matched:
            return matched.group("id")
        anchor_id = str(anchor.get("id", "")).strip()
        anchor_match = _MATCH_ID_FROM_ANCHOR_RE.match(anchor_id)
        if anchor_match:
            return anchor_match.group("id")
        return None

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
            ".match-status-label",
            ".tag",
            '[data-cy="matchStatus"]',
            ".marker",
            ".result",
            ".match-status",
            ".status",
            ".score",
        ])
        return status or ""

    def _extract_scores(self, container) -> tuple[int | None, int | None]:
        home_raw = self._text_first(container, [".r1"])
        away_raw = self._text_first(container, [".r2"])
        return self._to_int(home_raw), self._to_int(away_raw)

    @staticmethod
    def _to_int(value: str) -> int | None:
        value = value.strip()
        if not value:
            return None
        return int(value) if value.isdigit() else None

    @staticmethod
    def _text_first(container, selectors: list[str]) -> str:
        for selector in selectors:
            node = container.select_one(selector)
            if node:
                text = node.get_text(" ", strip=True)
                if text:
                    return text
        return ""
