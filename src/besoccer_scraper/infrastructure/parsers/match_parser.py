from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from besoccer_scraper.domain.entities import Match

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None


class MatchParser:
    _EVENT_STATUS_MAP = {
        "EventCompleted": "FIN",
        "EventScheduled": "SCH",
        "EventPostponed": "PST",
        "EventCancelled": "CANC",
        "EventAbandoned": "ABD",
        "EventDelayed": "DLY",
        "EventRescheduled": "RSC",
        "EventLive": "LIVE",
        "EventInProgress": "LIVE",
    }
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
            "venue": self._extract_venue(page_data),
            "status": self._extract_status(page_data),
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
        if not home_team or not away_team:
            metadata_home = self._extract_metadata_value(page_data, ("home_team_name", "homeTeamName", "localTeamName"))
            metadata_away = self._extract_metadata_value(page_data, ("away_team_name", "awayTeamName", "visitorTeamName"))
            if metadata_home and metadata_away:
                home_team, away_team = metadata_home.strip(), metadata_away.strip()
                metadata["home_team_name"] = home_team
                metadata["away_team_name"] = away_team
        stats_json = self._extract_stats(page_data, html=html)
        events_json = self._extract_events(page_data, html)
        metadata["parser_debug_counts"] = self._build_parser_debug_counts(html)

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
                "home_team_name": home_team,
                "away_team_name": away_team,
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

    def _extract_venue(self, payload: dict[str, Any]) -> str | None:
        location = self._deep_find(payload, "location")
        if isinstance(location, dict):
            name = location.get("name")
            if name not in (None, ""):
                return str(name)
        return self._extract_metadata_value(payload, ("venue", "stadium", "stadiumName"))

    def _extract_status(self, payload: dict[str, Any]) -> str | None:
        event_status = self._extract_metadata_value(payload, ("eventStatus",))
        if event_status:
            normalized = str(event_status).strip()
            normalized = normalized.rsplit("/", 1)[-1]
            return self._EVENT_STATUS_MAP.get(normalized, self._EVENT_STATUS_MAP.get(str(event_status).strip(), str(event_status).strip()))
        return self._extract_metadata_value(payload, ("status", "matchStatus", "state"))

    def _extract_score(self, payload: dict[str, Any], html: str) -> str | None:
        home_goals = self._deep_find(payload, "homeScore") or self._deep_find(payload, "localGoals")
        away_goals = self._deep_find(payload, "awayScore") or self._deep_find(payload, "visitorGoals")
        if home_goals is not None and away_goals is not None:
            return f"{home_goals}-{away_goals}"
        score_match = re.search(r'"(?:marcador|score)"\s*:\s*"(?P<score>\d+\s*[-:]\s*\d+)"', html, re.IGNORECASE)
        if score_match:
            return score_match.group("score").replace(":", "-").replace(" ", "")
        return None

    def _extract_stats(self, payload: dict[str, Any], *, html: str) -> dict[str, Any]:
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

        if normalized:
            return normalized

        return self._extract_stats_from_html(html)

    def _extract_stats_from_html(self, html: str) -> dict[str, Any]:
        if BeautifulSoup is None:
            return self._extract_stats_from_html_regex(html)
        soup = BeautifulSoup(html, "html.parser")
        panel = soup.select_one("#mod_stats")
        if panel is None:
            return {}
        return self._extract_stats_from_panel_text_and_rows(str(panel), panel.get_text(" ", strip=True))

    def _extract_stats_from_html_regex(self, html: str) -> dict[str, Any]:
        module_match = re.search(
            r"""<(?:section|div)[^>]+id=["']mod_stats["'][^>]*>(?P<body>.*?)</(?:section|div)>""",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not module_match:
            return {}
        return self._extract_stats_from_panel_text_and_rows(module_match.group("body"), self._clean_html_text(module_match.group("body")))

    def _extract_stats_from_panel_text_and_rows(self, body_html: str, module_text: str) -> dict[str, Any]:
        fallback_stats: dict[str, Any] = {}
        partial_stats: dict[str, Any] = {}

        for raw_row in re.findall(r"<tr\b[^>]*>(?P<row>.*?)</tr>", body_html, flags=re.IGNORECASE | re.DOTALL):
            cells = re.findall(r"<t[dh]\b[^>]*>(?P<cell>.*?)</t[dh]>", raw_row, flags=re.IGNORECASE | re.DOTALL)
            cleaned_cells = [self._clean_html_text(cell) for cell in cells]
            cleaned_cells = [cell for cell in cleaned_cells if cell]
            if len(cleaned_cells) < 3:
                continue

            home_value, raw_key, away_value = cleaned_cells[0], cleaned_cells[1], cleaned_cells[2]
            normalized_key = self._normalize_stat_key(raw_key)
            pair_payload = {"home": home_value, "away": away_value}

            if normalized_key in {
                "possession",
                "shots_on_target",
                "shots_total",
                "corners",
                "fouls",
                "yellow_cards",
                "red_cards",
            }:
                fallback_stats[normalized_key] = pair_payload
            else:
                partial_stats[normalized_key] = pair_payload

        # Tolerant fallback for non-table structures (div-based stats).
        if module_text:
            label_aliases: dict[str, tuple[str, ...]] = {
                "possession": ("Posesión", "Posesion"),
                "shots_total": ("Remates",),
                "shots_on_target": ("Remates a puerta",),
                "corners": ("Saques de esquina", "Corners"),
                "fouls": ("Faltas",),
                "yellow_cards": ("Tarjetas",),
            }
            for stat_key, labels in label_aliases.items():
                if stat_key in fallback_stats:
                    continue
                for label in labels:
                    pattern = re.compile(
                        rf"(?P<home>\d+%?)\s*{re.escape(label)}\s*(?P<away>\d+%?)",
                        flags=re.IGNORECASE,
                    )
                    match = pattern.search(module_text)
                    if match:
                        fallback_stats[stat_key] = {"home": match.group("home"), "away": match.group("away")}
                        break

        if partial_stats:
            fallback_stats["stats_json"] = partial_stats
        return fallback_stats

    @staticmethod
    def _clean_html_text(value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = re.sub(r"&nbsp;|&#160;", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_events(self, payload: dict[str, Any], html: str) -> list[dict[str, Any]]:
        if BeautifulSoup is None:
            return self._extract_events_regex(payload, html)
        soup = BeautifulSoup(html, "html.parser")
        panel = soup.select_one("#events-goals")
        events: list[dict[str, Any]] = []
        if panel is not None:
            rows = panel.select(".table-played-match")
            if rows:
                for row in rows:
                    if not self._is_goal_row(row):
                        continue
                    minute_info = self._extract_goal_minute(row)
                    minute_raw = minute_info.get("minute_raw") or ""
                    if minute_info.get("minute") is None:
                        continue
                    player_name, assist_player_name = self._extract_goal_players(row, soup=soup)
                    text_player = player_name if player_name else "unknown"
                    parsed = self._build_goal_event({"type": "goal", "minute": minute_raw, "text": f"{minute_raw} {text_player} goal", "player": player_name, "side": self._extract_goal_side_from_row(str(row))})
                    if parsed is not None:
                        parsed["assist_player_name"] = assist_player_name
                        events.append(parsed)
                return self._dedupe_events(events)
            panel_text = panel.get_text(" ", strip=True)
            return self._extract_text_goals(panel_text)
        return self._extract_events_regex(payload, html)

    def _extract_events_regex(self, payload: dict[str, Any], html: str) -> list[dict[str, Any]]:
        goals_section = re.search(r"""<section[^>]+id=["']events-goals["'][^>]*>(?P<body>.*?)</section>""", html, flags=re.IGNORECASE | re.DOTALL)
        events: list[dict[str, Any]] = []

        # Prioridad: usar solo #events-goals cuando exista.
        if goals_section:
            body = goals_section.group("body")
            rows = re.findall(
                r'(<div[^>]*class="[^"]*table-played-match[^"]*"[^>]*>.*?)(?=<div[^>]*class="[^"]*table-played-match|$)',
                body,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if rows:
                for row in rows:
                    if not self._is_goal_row(row):
                        continue
                    minute_text = self._extract_goal_minute_from_block(row)
                    minute_raw = self._normalize_minute_raw(minute_text)
                    player_name = self._extract_goal_player_from_row(row, body=body)
                    if not player_name:
                        continue
                    parsed = self._build_goal_event(
                        {
                            "type": "goal",
                            "minute": minute_raw,
                            "text": f"{minute_raw} {player_name} goal".strip(),
                            "player": player_name,
                            "side": self._extract_goal_side_from_row(row),
                        }
                    )
                    if parsed is not None:
                        parsed["assist_player_name"] = self._extract_assist_player_from_row(row)
                        events.append(parsed)
                return self._dedupe_events(events)

            # Fallback textual para HTML mínimo (cuando existe #events-goals pero sin rows estructurados).
            return self._extract_text_goals(self._clean_html_text(body))

        # Fallback: timeline JSON filtrando tipos estrictos de gol.
        raw_events = self._deep_find(payload, "events") or self._deep_find(payload, "timeline") or []
        if isinstance(raw_events, list):
            for event in raw_events:
                parsed = self._build_goal_event(event)
                if parsed is not None:
                    events.append(parsed)
        return self._dedupe_events(events)

    def _extract_text_goals(self, text: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for match in re.finditer(r"(?P<minute>\d{1,3}(?:\+\d+)?)['’]?\s+(?P<player>.+?)\s+goal\b", text, flags=re.IGNORECASE):
            minute_raw = self._normalize_minute_raw(match.group("minute"))
            player_name = self._clean_player_name(match.group("player"))
            if not self._is_valid_goal_player_name(player_name):
                continue
            parsed = self._build_goal_event({"type": "goal", "minute": minute_raw, "text": f"{minute_raw} {player_name} goal", "player": player_name, "side": "unknown"})
            if parsed is not None:
                events.append(parsed)
        return self._dedupe_goal_events(events)

    def _build_parser_debug_counts(self, html: str) -> dict[str, Any]:
        if BeautifulSoup is None:
            clean = self._clean_html_text(html)
            return {"events_goals_found": 'id="events-goals"' in html or "id='events-goals'" in html, "goal_rows_found": len(re.findall(r"table-played-match", html)), "goal_imgs_found": len(re.findall(r'alt="Gol"', html)), "accion1_imgs_found": len(re.findall(r"accion1", html)), "event1_nodes_found": len(re.findall(r"event-1", html)), "mod_stats_found": 'id="mod_stats"' in html or "id='mod_stats'" in html, "stats_rows_found": len(re.findall(r"<tr\\b", html)), "stats_text_has_posesion": "Posesión" in clean}
        soup = BeautifulSoup(html, "html.parser")
        return {
            "events_goals_found": bool(soup.select_one("#events-goals")),
            "goal_rows_found": len(soup.select("#events-goals .table-played-match")),
            "goal_imgs_found": len(soup.select('#events-goals img[alt="Gol"]')),
            "accion1_imgs_found": len(soup.select('#events-goals img[src*="accion1"]')),
            "event1_nodes_found": len(soup.select("#events-goals .event-1")),
            "mod_stats_found": bool(soup.select_one("#mod_stats")),
            "stats_rows_found": len(soup.select("#mod_stats tr")),
            "stats_text_has_posesion": "Posesión" in soup.get_text(" ", strip=True),
        }

    def _extract_goal_player_from_soup_row(self, row: Any, soup: Any) -> str | None:
        for a in row.select('a[href^="#popup_event"]'):
            popup = soup.select_one(a.get("href"))
            if popup:
                for item in popup.select(".right-content, .event-item, li, .table-played-match"):
                    if item.select_one(".event-1") or item.select_one('img[alt="Gol"]') or item.select_one('img[src*="accion1"]'):
                        main = item.select_one("a.main-text")
                        if main:
                            name = self._clean_player_name(main.get_text(" ", strip=True))
                            if self._is_valid_goal_player_name(name):
                                return name
        for a in row.select('a[data-cy="event"]'):
            classes = " ".join(a.get("class", []))
            if "color-grey2" in classes:
                continue
            name = self._clean_player_name(a.get_text(" ", strip=True))
            if self._is_valid_goal_player_name(name):
                return name
        return None

    def _extract_assist_player_from_soup_row(self, row: Any) -> str | None:
        for a in row.select('a.color-grey2, .event-22 a'):
            name = self._clean_player_name(a.get_text(" ", strip=True))
            if self._is_valid_goal_player_name(name):
                return name
        names: list[str] = []
        for item in row.select('a[data-cy="event"]'):
            name = self._clean_player_name(item.get_text(" ", strip=True))
            if self._is_valid_goal_player_name(name):
                names.append(name)
        return names[1] if len(names) > 1 else None

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
        lowered_text = text.lower()
        if not self._is_strict_goal_event(event_type=event_type, text=lowered_text):
            return None

        minute_raw = str(event.get("minute") or event.get("time") or self._extract_minute_from_text(text) or "").strip()
        minute, added_time = self._parse_minute(minute_raw)
        player_name = event.get("player") or event.get("playerName") or event.get("name") or None
        if not player_name:
            player_name = self._extract_player_name_from_text(text, html_fragment=str(event.get("html") or ""))

        player_name = self._clean_player_name(player_name)

        return {
            "event_type": "goal",
            "minute_raw": minute_raw or None,
            "minute": minute,
            "added_time": added_time,
            "half": self.classify_half_by_minute(minute=minute, added_time=added_time, raw_text=text),
            "player_name": player_name,
            "team_side": self._normalize_team_side(event.get("team") or event.get("side") or event.get("teamSide")) or "unknown",
            "score_after": event.get("score") or event.get("scoreAfter") or None,
            "is_own_goal": "own goal" in lowered_text or "en propia" in lowered_text,
            "is_penalty": "pen" in lowered_text,
            "raw_text": text or None,
        }

    @staticmethod
    def _is_strict_goal_event(*, event_type: str, text: str) -> bool:
        goal_tokens = ("goal", "gol", "penalty scored", "own goal", "en propia")
        if not any(token in event_type for token in goal_tokens) and not any(token in text for token in goal_tokens):
            return False
        blocked_tokens = (
            "substitution",
            "substitucion",
            "substitución",
            "yellow",
            "red card",
            "tarjeta",
            "injury",
            "lesion",
            "lesión",
        )
        return not any(token in event_type or token in text for token in blocked_tokens)

    @staticmethod
    def _extract_player_name_from_text(text: str, html_fragment: str = "") -> str | None:
        if html_fragment:
            anchors = re.findall(r"<a\b[^>]*>(?P<label>.*?)</a>", html_fragment, flags=re.IGNORECASE | re.DOTALL)
            visible = [MatchParser._clean_html_text(chunk) for chunk in anchors]
            visible = [chunk for chunk in visible if chunk]
            if visible:
                return visible[-1]
        if not text:
            return None
        cleaned = re.sub(r"^\s*\d{1,3}(?:\+\d+)?'\s*", "", text).strip()
        cleaned = re.sub(r"\b(goal|gol|penalty\s+scored|own\s+goal)\b.*$", "", cleaned, flags=re.I).strip(" -,:;")
        return cleaned or None

    @staticmethod
    def _clean_player_name(value: Any) -> str | None:
        if value in (None, ""):
            return None
        cleaned = MatchParser._clean_html_text(str(value))
        cleaned = re.sub(r"\b(goal|gol|penalty\s+scored|own\s+goal)\b.*$", "", cleaned, flags=re.I).strip(" -,:;")
        return cleaned or None

    def _dedupe_goal_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for event in events:
            minute_key = str(event.get("minute_raw") or self._normalize_minute_key(event.get("minute"), event.get("added_time"), event.get("minute_raw")))
            player_key = re.sub(r"\s+", " ", str(event.get("player_name") or "").strip().lower())
            assist_key = re.sub(r"\s+", " ", str(event.get("assist_player_name") or "").strip().lower())
            side_key = str(event.get("team_side") or "").strip().lower()
            key = (str(event.get("event_type") or "").strip().lower(), minute_key, player_key, assist_key, side_key)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(event)
        return deduped

    def _dedupe_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._dedupe_goal_events(events)

    @staticmethod
    def _is_goal_row(row: Any) -> bool:
        if hasattr(row, "select_one"):
            text = row.get_text(" ", strip=True).lower()
            return bool(
                row.select_one('img[alt="Gol"]')
                or row.select_one('img[src*="accion1"]')
                or row.select_one(".event-1")
                or ("goal" in text)
            )
        lowered = str(row).lower()
        return ('alt="gol"' in lowered) or ("accion1" in lowered) or ('event-1' in lowered) or ("goal" in lowered)

    @staticmethod
    def _extract_goal_side_from_row(row: str) -> str | None:
        classes = re.search(r'class="([^"]+)"', row, flags=re.IGNORECASE)
        if not classes:
            return None
        value = classes.group(1).lower()
        if "left" in value or "local" in value:
            return "home"
        if "right" in value or "visitor" in value:
            return "away"
        return None

    @staticmethod
    def _extract_goal_minute_from_block(block: str) -> str:
        raw = MatchParser._clean_html_text(block)
        m = re.search(r"\b(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\b", raw)
        if not m:
            return ""
        if m.group(2):
            return f"{m.group(1)}+{m.group(2)}"
        return m.group(1)

    def _extract_goal_minute(self, row: Any) -> dict[str, Any]:
        minute_text = ""
        if hasattr(row, "select_one"):
            minute_node = row.select_one(".min, .minute")
            minute_text = minute_node.get_text(" ", strip=True) if minute_node else ""
        else:
            minute_text = self._extract_goal_minute_from_block(str(row))
        return self._normalize_minute(minute_text)

    def _normalize_minute(self, text: str) -> dict[str, Any]:
        minute_raw = self._normalize_minute_raw(text)
        minute, added_time = self._parse_minute(minute_raw)
        return {
            "minute_raw": minute_raw or None,
            "minute": minute,
            "added_time": added_time,
            "half": self.classify_half_by_minute(minute=minute, added_time=added_time, raw_text=minute_raw),
        }

    @staticmethod
    def _normalize_minute_raw(value: str) -> str:
        cleaned = re.sub(r"\s+", "", str(value or ""))
        cleaned = cleaned.replace("’", "").replace("'", "")
        return cleaned

    def _extract_goal_player_from_row(self, row: str, *, body: str) -> str | None:
        popup_link = re.search(r'href="(?P<ref>#popup_event[^"]+)"', row, flags=re.IGNORECASE)
        if popup_link:
            ref = re.escape(popup_link.group("ref").lstrip("#"))
            popup_match = re.search(rf'<[^>]+id="{ref}"[^>]*>(?P<popup>.*?)</[^>]+>', body, flags=re.IGNORECASE | re.DOTALL)
            if popup_match and 'event-1' in popup_match.group("popup").lower():
                main = re.search(r'<a[^>]*class="[^"]*main-text[^"]*"[^>]*>(?P<n>.*?)</a>', popup_match.group("popup"), flags=re.IGNORECASE | re.DOTALL)
                if main:
                    text = self._clean_player_name(main.group("n"))
                    if self._is_valid_goal_player_name(text):
                        return text

        anchors = re.findall(r'<a\b(?P<attrs>[^>]*)data-cy="event"(?P<attrs2>[^>]*)>(?P<label>.*?)</a>', row, flags=re.IGNORECASE | re.DOTALL)
        for attrs, attrs2, label in anchors:
            attrs_all = f"{attrs} {attrs2}".lower()
            if "color-grey2" in attrs_all:
                continue
            text = self._clean_player_name(label)
            if self._is_valid_goal_player_name(text):
                return text
        return None

    def _extract_goal_players(self, row: Any, soup: Any = None) -> tuple[str | None, str | None]:
        if hasattr(row, "select_one"):
            player_name = self._extract_goal_player_from_soup_row(row, soup)
            assist_player_name = self._extract_assist_player_from_soup_row(row)

            # Fallback explícito: anchors visibles en orden, ignorando vacíos y etiquetas no-jugador.
            if not player_name:
                for a in row.select('a[data-cy="event"]'):
                    attrs = " ".join(a.get("class", []))
                    text = self._clean_player_name(a.get_text(" ", strip=True))
                    if not self._is_valid_goal_player_name(text):
                        continue
                    if "color-grey2" in attrs:
                        if not assist_player_name:
                            assist_player_name = text
                        continue
                    player_name = text
                    break
            if not assist_player_name:
                seen_primary = False
                for a in row.select('a[data-cy="event"]'):
                    attrs = " ".join(a.get("class", []))
                    text = self._clean_player_name(a.get_text(" ", strip=True))
                    if not self._is_valid_goal_player_name(text):
                        continue
                    if "color-grey2" in attrs:
                        assist_player_name = text
                        break
                    if seen_primary:
                        assist_player_name = text
                        break
                    if player_name and text == player_name:
                        seen_primary = True
            return player_name, assist_player_name
        row_text = str(row)
        return self._extract_goal_player_from_row(row_text, body=row_text), self._extract_assist_player_from_row(row_text)

    @staticmethod
    def _is_valid_goal_player_name(text: str | None) -> bool:
        if not text:
            return False
        lowered = text.lower()
        if lowered in {"sustituciones", "substitutions", "gol", "asistencia"}:
            return False
        if text in {"+2"}:
            return False
        if "<" in text or "</" in text:
            return False
        if re.fullmatch(r"\+\d{1,2}", text):
            return False
        return True

    def _extract_assist_player_from_row(self, row: str) -> str | None:
        for anchor in re.findall(r'<a\b[^>]*class="[^"]*(?:color-grey2|event-22)[^"]*"[^>]*>(?P<label>.*?)</a>', row, flags=re.IGNORECASE | re.DOTALL):
            text = self._clean_player_name(anchor)
            if text:
                return text
        names: list[str] = []
        for _, _, label in re.findall(r'<a\b(?P<attrs>[^>]*)data-cy="event"(?P<attrs2>[^>]*)>(?P<label>.*?)</a>', row, flags=re.IGNORECASE | re.DOTALL):
            text = self._clean_player_name(label)
            if self._is_valid_goal_player_name(text):
                names.append(text)
        return names[1] if len(names) > 1 else None

    @staticmethod
    def _normalize_minute_key(minute: Any, added_time: Any, minute_raw: Any) -> str:
        if isinstance(minute, int):
            if isinstance(added_time, int):
                return f"{minute}+{added_time}"
            return str(minute)
        parsed_minute, parsed_added = MatchParser._parse_minute(str(minute_raw or ""))
        if parsed_minute is None:
            return ""
        if parsed_added is not None:
            return f"{parsed_minute}+{parsed_added}"
        return str(parsed_minute)

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
        key = unicodedata.normalize("NFKD", key).encode("ascii", "ignore").decode("ascii")
        key = key.strip().lower().replace("%", " percent ")
        key = re.sub(r"[^a-z0-9]+", "_", key)
        key = re.sub(r"_+", "_", key).strip("_")
        aliases = {
            "possession_percent": "possession",
            "total_shots": "shots_total",
            "shots_total": "shots_total",
            "shots_on_target": "shots_on_target",
            "corners": "corners",
            "posesion": "possession",
            "posesion_percent": "possession",
            "remates": "shots_total",
            "tiros": "shots_total",
            "remates_a_puerta": "shots_on_target",
            "tiros_a_puerta": "shots_on_target",
            "saques_de_esquina": "corners",
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
