from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from besoccer_scraper.domain.entities import Match


class MatchParser:
    _ID_PATTERNS = (
        re.compile(r"/partido/[^/]+/[^/]+/(?P<id>\d+)", re.IGNORECASE),
        re.compile(r"/partido/[^/]+/(?P<id>\d+)", re.IGNORECASE),
        re.compile(r'"matchId"\s*:\s*"?(?P<id>\d+)"?', re.IGNORECASE),
    )
    _TITLE_RE = re.compile(r"<title>(?P<title>.*?)</title>", re.IGNORECASE | re.DOTALL)
    _KICKOFF_RE = re.compile(r'"startDate"\s*:\s*"(?P<kickoff>[^"]+)"', re.IGNORECASE)
    _JSON_LD_RE = re.compile(
        r'<script[^>]*type="application/ld\+json"[^>]*>(?P<body>.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    _MARKER_BLOCK_RE = re.compile(r'window\.__INITIAL_STATE__\s*=\s*(?P<json>\{.*?\})\s*;?', re.DOTALL)
    _TEAM_POSITIONS = ("home", "local", "left", "away", "visitor", "right")

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
        page_data = self._extract_page_data(html)

        fallback_round = self._extract_round_from_text(html)
        derived_season_key = self._derive_season_key(
            season_key=season_key,
            round_label=round_label,
            competition_slug=competition_slug,
            kickoff_at=kickoff_at,
            page_data=page_data,
        )
        metadata = {
            "competition_name": self._extract_metadata_value(page_data, ("competition_name", "competitionName", "leagueName")),
            "season_key": derived_season_key
            or self._extract_metadata_value(page_data, ("season_key", "seasonKey", "season", "season_name")),
            "round_label": round_label
            or self._extract_metadata_value(page_data, ("round_label", "roundLabel", "matchday", "journey", "round")),
            "venue": self._extract_metadata_value(page_data, ("venue", "stadium", "stadiumName")),
            "status": self._extract_metadata_value(page_data, ("status", "matchStatus", "state")),
            "score": self._extract_score(page_data, html),
            "date_utc": self._format_utc_datetime(kickoff_at),
        }
        if not metadata["round_label"] and fallback_round:
            metadata["round_label"] = fallback_round
        metadata["canonical_url"] = self._extract_canonical(html) or url
        metadata["title"] = self._extract_title(html)
        if not metadata.get("competition_name"):
            metadata["competition_name"] = self._extract_competition_from_title(metadata.get("title") or "")
        if not metadata.get("score"):
            metadata["score"] = self._extract_score_from_description(page_data)
        metadata["home_team_name"] = home_team
        metadata["away_team_name"] = away_team
        stats_json = self._extract_stats(page_data)
        events_json = self._extract_events(page_data, html)

        if not home_team or not away_team:
            raise ValueError("Unable to extract teams")
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
                "round_label": metadata["round_label"],
                "season_key": metadata["season_key"],
                "metadata": metadata,
                "stats_json": stats_json,
                "events_json": events_json,
            },
        )

    def _extract_match_id(self, *, url: str, html: str) -> str:
        for pattern in self._ID_PATTERNS:
            matched = pattern.search(url) or pattern.search(html)
            if matched:
                return matched.group("id")
        raise ValueError("Unable to extract match id from URL/HTML")

    def _extract_teams(self, html: str) -> tuple[str, str]:
        # Fuente 1: título con patrón "Estadísticas X vs Y"
        title_match = self._TITLE_RE.search(html)
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group("title")).strip()
            head = title.split("|")[0].strip()
            for separator in (" vs ", " vs. ", " - "):
                if separator in head:
                    left, right = head.split(separator, 1)
                    left = left.replace("Estadísticas", "").strip(" ,")
                    right = right.split(",")[0].strip(" ,")
                    if left and right:
                        return left.strip(), right.strip()

        # Fuente 2: bloque visual/estado JSON con home-away o local-visitor.
        page_data = self._extract_page_data(html)
        home_team = self._extract_metadata_value(page_data, ("home", "local", "homeTeam", "localTeam"))
        away_team = self._extract_metadata_value(page_data, ("away", "visitor", "awayTeam", "visitorTeam"))
        if home_team and away_team:
            return home_team.strip(), away_team.strip()

        # Fuente 3: description con marcador.
        desc_score = re.search(r"([A-Za-zÀ-ÿ\s\.\-]+)\s+\d+\s*[-:]\s*\d+\s+([A-Za-zÀ-ÿ\s\.\-]+)", html)
        if desc_score:
            return desc_score.group(1).strip(), desc_score.group(2).strip()
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

    def _extract_page_data(self, html: str) -> dict[str, Any]:
        aggregate: dict[str, Any] = {}
        for block in self._JSON_LD_RE.finditer(html):
            body = block.group("body").strip()
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                aggregate.update(parsed)
        marker_match = self._MARKER_BLOCK_RE.search(html)
        if marker_match:
            try:
                parsed = json.loads(marker_match.group("json"))
                if isinstance(parsed, dict):
                    aggregate.update(parsed)
            except json.JSONDecodeError:
                pass
        return aggregate

    def _extract_metadata_value(self, payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        for key in keys:
            value = self._deep_find(payload, key)
            if value not in (None, ""):
                return str(value)
        return None

    def _extract_score(self, payload: dict[str, Any], html: str) -> str | None:
        home_goals = self._deep_find(payload, "homeScore") or self._deep_find(payload, "localGoals")
        away_goals = self._deep_find(payload, "awayScore") or self._deep_find(payload, "visitorGoals")
        if home_goals is not None and away_goals is not None:
            return f"{home_goals}-{away_goals}"
        score_match = re.search(r'"(?:marcador|score)"\s*:\s*"(?P<score>\d+\s*[-:]\s*\d+)"', html, re.IGNORECASE)
        if score_match:
            return score_match.group("score").replace(":", "-").replace(" ", "")
        return None

    def _extract_stats(self, payload: dict[str, Any]) -> dict[str, Any]:
        stats_bucket = self._deep_find(payload, "stats") or self._deep_find(payload, "statistics") or {}
        normalized: dict[str, Any] = {}
        if isinstance(stats_bucket, dict):
            items = stats_bucket.items()
        elif isinstance(stats_bucket, list):
            items = []
            for entry in stats_bucket:
                if isinstance(entry, dict) and "name" in entry:
                    items.append((entry.get("name"), entry.get("value")))
        else:
            items = []

        for raw_key, value in items:
            if raw_key is None:
                continue
            key = self._normalize_stat_key(str(raw_key))
            normalized[key] = value
        return normalized

    def _extract_events(self, payload: dict[str, Any], html: str) -> list[dict[str, Any]]:
        raw_events = self._deep_find(payload, "events") or self._deep_find(payload, "timeline") or []
        events: list[dict[str, Any]] = []
        if isinstance(raw_events, list):
            for event in raw_events:
                parsed = self._build_goal_event(event)
                if parsed is not None:
                    events.append(parsed)

        if events:
            return events

        # Fallback extraction from plain-text timeline strings.
        goals_section = re.search(r'id="events-goals"[^>]*>(?P<body>.*?)</section>', html, flags=re.IGNORECASE | re.DOTALL)
        body = goals_section.group("body") if goals_section else html
        chunks = re.findall(r"(\d{1,3}(?:\+\d+)?'[^']*?)(?=\d{1,3}(?:\+\d+)?'|$)", body, flags=re.IGNORECASE)
        for line in chunks:
            parsed = self._build_goal_event({"type": "goal", "text": line.strip()})
            if parsed:
                events.append(parsed)
        return events

    @staticmethod
    def _extract_canonical(html: str) -> str | None:
        m = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html, re.I)
        return m.group(1).strip() if m else None

    def _extract_title(self, html: str) -> str | None:
        m = self._TITLE_RE.search(html)
        return re.sub(r"\s+", " ", m.group("title")).strip() if m else None

    @staticmethod
    def _extract_round_from_text(html: str) -> str | None:
        m = re.search(r"Jornada\s+(\d+)", html, re.I)
        return f"JORNADA{int(m.group(1))}" if m else None

    @staticmethod
    def _extract_competition_from_title(title: str) -> str | None:
        m = re.search(r",\s*([^,]+Jornada\s+\d+)", title, re.I)
        if m:
            return re.sub(r"\s+Jornada\s+\d+", "", m.group(1), flags=re.I).strip()
        return None

    @staticmethod
    def _extract_score_from_description(payload: dict[str, Any]) -> str | None:
        desc = str(payload.get("description") or "")
        m = re.search(r"\b(\d+)\s*[-:]\s*(\d+)\b", desc)
        return f"{m.group(1)}-{m.group(2)}" if m else None

    def _build_goal_event(self, event: Any) -> dict[str, Any] | None:
        if not isinstance(event, dict):
            return None
        event_type = str(event.get("type") or event.get("eventType") or event.get("name") or "").lower()
        text = str(event.get("text") or event.get("description") or "").strip()
        if "goal" not in event_type and "gol" not in event_type and "goal" not in text.lower() and "gol" not in text.lower():
            return None

        minute_raw = str(event.get("minute") or event.get("time") or self._extract_minute_from_text(text) or "").strip()
        minute, added_time = self._parse_minute(minute_raw)
        lowered_text = text.lower()
        return {
            "event_type": "goal",
            "minute_raw": minute_raw or None,
            "minute": minute,
            "added_time": added_time,
            "half": self.classify_half_by_minute(minute=minute, added_time=added_time, raw_text=text),
            "player_name": event.get("player") or event.get("playerName") or None,
            "team_side": self._normalize_team_side(event.get("team") or event.get("side") or event.get("teamSide")),
            "score_after": event.get("score") or event.get("scoreAfter") or None,
            "is_own_goal": "own goal" in lowered_text or "en propia" in lowered_text,
            "is_penalty": "pen" in lowered_text,
            "raw_text": text or None,
        }

    @staticmethod
    def classify_half_by_minute(minute: int | None, added_time: int | None, raw_text: str | None = None) -> str:
        if minute is None:
            return "unknown"
        if 1 <= minute <= 45:
            return "first_half"
        if minute == 45 and (added_time or 0) > 0:
            return "first_half"
        if 46 <= minute <= 90:
            return "second_half"
        if minute == 90 and (added_time or 0) > 0:
            return "second_half"
        if minute > 90 and (added_time or 0) == 0:
            lowered = (raw_text or "").lower()
            if any(token in lowered for token in ("extra", "aet", "prórroga", "overtime")):
                return "extra_time"
            if any(token in lowered for token in ("pen", "shootout", "penalt")):
                return "penalties"
            return "unknown"
        return "unknown"

    @staticmethod
    def _normalize_stat_key(key: str) -> str:
        key = key.strip().lower().replace("%", " percent ")
        key = re.sub(r"[^a-z0-9]+", "_", key)
        key = re.sub(r"_+", "_", key).strip("_")
        aliases = {
            "possession_percent": "possession",
            "total_shots": "shots_total",
            "shots_total": "shots_total",
            "shots_on_target": "shots_on_target",
            "corners": "corners",
            "fouls": "fouls",
            "yellow_cards": "yellow_cards",
            "red_cards": "red_cards",
        }
        return aliases.get(key, key)

    @staticmethod
    def _parse_minute(minute_raw: str) -> tuple[int | None, int | None]:
        if not minute_raw:
            return None, None
        match = re.search(r"(?P<base>\d+)(?:\s*\+\s*(?P<added>\d+))?", minute_raw)
        if not match:
            return None, None
        base = int(match.group("base"))
        added_group = match.group("added")
        return base, int(added_group) if added_group is not None else None

    @staticmethod
    def _extract_minute_from_text(text: str) -> str | None:
        match = re.search(r"\b\d{1,3}(?:\+\d{1,2})?\b", text)
        return match.group(0) if match else None

    def _deep_find(self, obj: Any, key: str) -> Any:
        if isinstance(obj, dict):
            for k, value in obj.items():
                if str(k).lower() == key.lower():
                    return value
                nested = self._deep_find(value, key)
                if nested is not None:
                    return nested
        elif isinstance(obj, list):
            for item in obj:
                nested = self._deep_find(item, key)
                if nested is not None:
                    return nested
        return None

    def _normalize_team_side(self, side: Any) -> str | None:
        if side is None:
            return None
        value = str(side).strip().lower()
        if value in {"home", "local", "left"}:
            return "home"
        if value in {"away", "visitor", "right"}:
            return "away"
        return value or None

    @staticmethod
    def _format_utc_datetime(kickoff: datetime | None) -> str | None:
        if kickoff is None:
            return None
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        return kickoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    def _derive_season_key(
        self,
        *,
        season_key: str | None,
        round_label: str | None,
        competition_slug: str,
        kickoff_at: datetime | None,
        page_data: dict[str, Any],
    ) -> str:
        if season_key:
            return self._normalize_season_key(competition_slug=competition_slug, season_key=season_key)

        kickoff_year = self._extract_year_from_datetime(kickoff_at)
        if kickoff_year is None:
            kickoff_year = self._extract_year_from_iso(self._extract_metadata_value(page_data, ("startDate",)))
        if kickoff_year is not None:
            base_key = f"{competition_slug}-{kickoff_year}"
            if round_label:
                base_key = f"{competition_slug}-{round_label}-{kickoff_year}"
            return self._normalize_season_key(competition_slug=competition_slug, season_key=base_key)

        match_date_utc = self._extract_metadata_value(page_data, ("match_date_utc",))
        json_ld_year = self._extract_year_from_iso(match_date_utc)
        if json_ld_year is not None:
            return self._normalize_season_key(competition_slug=competition_slug, season_key=f"{competition_slug}-{json_ld_year}")

        current_utc_year = datetime.now(timezone.utc).year
        return self._normalize_season_key(competition_slug=competition_slug, season_key=f"{competition_slug}-{current_utc_year}")

    @staticmethod
    def _extract_year_from_datetime(value: datetime | None) -> int | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).year

    @staticmethod
    def _extract_year_from_iso(value: str | None) -> int | None:
        if not value:
            return None
        raw = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).year

    @staticmethod
    def _normalize_season_key(*, competition_slug: str, season_key: str) -> str:
        if competition_slug == "clausura_mexico":
            year_match = re.search(r"(20\d{2})", season_key)
            year = year_match.group(1) if year_match else str(datetime.now(timezone.utc).year)
            return f"clausura-{year}"
        return season_key
