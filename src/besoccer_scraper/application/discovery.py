from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from besoccer_scraper.config.league_catalog import get_league_config
from besoccer_scraper.domain.policies import RequestPolicy
from besoccer_scraper.domain.repositories import UnitOfWork
from besoccer_scraper.domain.services import build_season_key
from besoccer_scraper.shared.exceptions import HttpFetchError, ScrapeBlockedError


@dataclass
class DiscoverCompetitionsUseCase:
    uow: UnitOfWork
    http_client: object
    parser: object
    request_policy: RequestPolicy

    def execute(self, source_url: str) -> int:
        html = self.http_client.get(source_url)
        competitions = self.parser.parse(html)
        count = self.uow.competitions.upsert_many(competitions)
        self.uow.commit()
        return count


@dataclass
class DiscoverMxTeamUseCase:
    uow: UnitOfWork
    http_client: object
    parser: object

    def execute(self, *, competition_slug: str, year: int, team_slug: str, dry_run: bool = True, print_urls: bool = False, persist: bool = False) -> list[dict[str, str]]:
        team_url = f"https://es.besoccer.com/equipo/partidos/{team_slug}/{year}"
        html = self.http_client.get(team_url)
        parsed = self.parser.parse(html, competition_slug)
        discovered: dict[str, dict[str, str]] = {}
        for match in parsed:
            source_match_id = str(match.payload.get("source_match_id") or match.external_id)
            relative_url = str(match.payload.get("relative_url", ""))
            if source_match_id in discovered:
                continue
            discovered[source_match_id] = {"source_match_id": source_match_id, "url": f"https://es.besoccer.com{relative_url}", "competition": competition_slug, "year": str(year), "team": team_slug}
        records = list(discovered.values())
        if persist and not dry_run:
            for record in records:
                self.uow.scrape_targets.insert(source_match_id=record["source_match_id"], source_url=record["url"], status="pending")
            self.uow.commit()
        if print_urls:
            for record in records:
                print(record["url"])
        return records


@dataclass(frozen=True)
class DiscoveryResult:
    competition: str
    season_key: str
    strategy: str
    targets_by_source_match_id: dict[str, dict[str, str]]
    targets_by_round: dict[str, list[dict[str, str]]]
    missing_rounds: list[str]
    duplicate_source_match_ids: list[str]
    unstable_rounds: list[str]
    coverage_status: str
    expected_matches: int
    persist_allowed: bool

    @property
    def rows(self) -> list[dict[str, str]]:
        return list(self.targets_by_source_match_id.values())

    @property
    def rounds_detected(self) -> int:
        return len(self.targets_by_round)

    @property
    def unique_match_ids(self) -> int:
        return len(self.targets_by_source_match_id)


@dataclass
class DiscoverMxSeasonUseCase:
    team_use_case: DiscoverMxTeamUseCase
    competition_parser: object
    http_client: object
    browser_renderer: object | None = None
    use_browser_fallback: bool = False
    expected_rounds: dict[str, int] = None  # type: ignore[assignment]
    browser_max_passes: int = 3
    liga_mx_matches_per_round: int = 9

    def __post_init__(self) -> None:
        if self.expected_rounds is None:
            self.expected_rounds = {"clausura_mexico": 17, "apertura_mexico": 17}

    def execute(self, *, competition_slug: str, year: int, max_teams: int | None = None, dry_run: bool = True, persist: bool = False, print_urls: bool = False, browser: bool | None = None, fallback_to_teams: bool = True, debug: bool = False, sample_size: int = 3, allow_partial: bool = False, require_complete: bool = False) -> list[dict[str, str]]:
        season_key = build_season_key(competition_slug, year)
        competition_url = f"https://es.besoccer.com/competicion/resultados/{competition_slug}/{year}"
        force_browser = competition_slug in {"clausura_mexico", "apertura_mexico"}
        use_browser = force_browser if browser is None else browser
        if browser is None and self.use_browser_fallback:
            use_browser = True

        discovered = self._discover_by_browser(competition_slug, season_key, competition_url, year, debug=debug) if use_browser else self._discover_by_rounds(competition_slug=competition_slug, season_key=season_key, competition_url=competition_url)
        if not discovered and not use_browser and self.use_browser_fallback:
            discovered = self._discover_by_browser(competition_slug, season_key, competition_url, year, debug=debug)
        if fallback_to_teams and self._should_fallback(discovered) and hasattr(self.team_use_case, "execute"):
            discovered = self._discover_by_teams(competition_slug=competition_slug, year=year, season_key=season_key, max_teams=max_teams)

        result = self._build_discovery_result(
            competition_slug=competition_slug,
            season_key=season_key,
            discovered=discovered,
            unstable_rounds=getattr(self, "_last_unstable_rounds", []),
        )
        rows = result.rows
        if print_urls:
            grouped: dict[str, list[str]] = {}
            for row in rows:
                normalized = self._normalize_round_label(str(row["round_label"]))
                grouped.setdefault(normalized, []).append(row["url"])
            for round_label in sorted(grouped.keys(), key=self._round_sort_key):
                print(f"[{round_label}]")
                for url in grouped[round_label]:
                    print(url)

        rounds_detected = result.rounds_detected
        rounds_expected = self.expected_rounds.get(competition_slug, rounds_detected)
        missing_rounds = result.missing_rounds
        expected_matches = result.expected_matches
        coverage_status = result.coverage_status
        print(f"competition={competition_slug}")
        print(f"year={year}")
        print(f"season_key={season_key}")
        print(f"strategy={result.strategy}")
        print(f"rounds_expected={rounds_expected}")
        print(f"rounds_attempted={self._last_rounds_attempted if hasattr(self, '_last_rounds_attempted') else rounds_expected}")
        print(f"rounds_detected={rounds_detected}")
        print(f"missing_rounds={missing_rounds}")
        print(f"targets_found={len(rows)}")
        print(f"unique_match_ids={result.unique_match_ids}")
        print(f"coverage_status={coverage_status}")
        persist_requested = persist and not dry_run
        persist_applied = persist_requested and (
            coverage_status == "complete" or (coverage_status != "complete" and allow_partial)
        )
        print(f"persist_requested={str(persist_requested).lower()}")
        print(f"persist_applied={str(persist_applied).lower()}")
        if persist_requested and coverage_status != "complete":
            print("reason=coverage_partial")
        grouped_ids: dict[str, list[str]] = {
            round_label: [str(target["source_match_id"]) for target in targets]
            for round_label, targets in result.targets_by_round.items()
        }
        for label in sorted(grouped_ids.keys(), key=self._round_sort_key):
            sample = grouped_ids[label][:sample_size]
            print(f"{label} count={len(grouped_ids[label])} sample_ids={sample}")
        print(f"targets_by_round={{{', '.join(f'{k}:{len(v)}' for k, v in sorted(grouped_ids.items(), key=lambda x: self._round_sort_key(x[0])))}}}")
        print(f"sample_ids_by_round={{{', '.join(f'{k}:{v[:sample_size]}' for k, v in sorted(grouped_ids.items(), key=lambda x: self._round_sort_key(x[0])))}}}")
        print(f"duplicate_source_match_ids={result.duplicate_source_match_ids}")
        print(f"unstable_rounds={result.unstable_rounds}")
        if debug and not rows:
            debug_path = Path("data/snapshots/errors") / f"mx_season_{competition_slug}_{year}_summary.json"
            if debug_path.exists():
                summary = json.loads(debug_path.read_text(encoding="utf-8"))
                print(f"Debug summary: {debug_path}")
                print(f"Debug HTML: {summary.get('after_cookie_html')}")
                print(f"html_length={summary.get('html_length')}")
                print(f"body_text_length={summary.get('body_text_length')}")
                print(f"round_options_found={summary.get('round_options_found')}")
                print(f"match_anchor_count_global={summary.get('match_anchor_count_global')}")
                print(f"match_anchor_count_scoped={summary.get('match_anchor_count_scoped')}")
        if require_complete and coverage_status != "complete":
            raise RuntimeError(
                f"Discovery incompleto para {competition_slug} {year}: rounds_detected={rounds_detected}/{rounds_expected} targets_found={len(rows)}/{expected_matches}"
            )
        if persist_requested and coverage_status != "complete" and not allow_partial:
            print("Discovery parcial: no se persiste sin --allow-partial")
            print(f"missing_rounds={missing_rounds}")
            return rows
        if persist_applied:
            inserted = 0
            updated = 0
            updated_safe = 0
            skipped_existing = 0
            for row in rows:
                outcome = self.team_use_case.uow.scrape_targets.upsert_target(source_name="besoccer", target_type="match_page", url=row["url"], source_match_id=row["source_match_id"], payload={"source_competition_slug": competition_slug, "season_key": season_key, "round_label": row["round_label"], "status": "pending", "metadata_json": {"discovery_strategy": "browser_dom_rounds", "last_discovery_strategy": "browser_dom_rounds", "coverage_status": coverage_status, "year": year, "competition": competition_slug, "last_seen_at": datetime.now(timezone.utc).isoformat(), "discovery_last_seen_at": datetime.now(timezone.utc).isoformat()}})
                if isinstance(outcome, dict):
                    inserted += 1 if outcome.get("inserted") else 0
                    updated += 1 if outcome.get("updated") else 0
                    updated_safe += 1 if outcome.get("updated_safe") else 0
                    skipped_existing += 1 if outcome.get("skipped_existing") else 0
                else:
                    inserted += 1
            self.team_use_case.uow.commit()
            db_total = self.team_use_case.uow.scrape_targets.count_by_competition_season(competition=competition_slug, season_key=season_key)
            print(f"inserted={inserted}")
            print(f"updated={updated}")
            print(f"updated_safe={updated_safe}")
            print(f"skipped_existing={skipped_existing}")
            print(f"db_total_for_season={db_total}")
            if (inserted + updated) > 0 and db_total == 0:
                raise RuntimeError("Persist verification failed: targets were written but audit filter cannot see them")
        return rows

    def _build_discovery_result(
        self,
        *,
        competition_slug: str,
        season_key: str,
        discovered: dict[str, dict[str, str]],
        unstable_rounds: list[str],
    ) -> DiscoveryResult:
        rows = list(discovered.values())
        rounds_expected = self.expected_rounds.get(competition_slug, len(rows))
        targets_by_round: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            normalized_round = self._normalize_round_label(str(row.get("round_label", "")))
            targets_by_round.setdefault(normalized_round, []).append(row)

        missing_rounds = [f"JORNADA{i}" for i in range(1, rounds_expected + 1) if f"JORNADA{i}" not in targets_by_round]
        expected_matches = 153 if competition_slug in {"clausura_mexico", "apertura_mexico"} else len(rows)
        matches_per_round_expected = self.liga_mx_matches_per_round if competition_slug in {"clausura_mexico", "apertura_mexico"} else 0
        rounds_have_expected_size = all(
            len(targets_by_round.get(f"JORNADA{i}", [])) == matches_per_round_expected
            for i in range(1, rounds_expected + 1)
        ) if matches_per_round_expected else True
        coverage_status = "complete" if len(targets_by_round) == rounds_expected and len(rows) == expected_matches and rounds_have_expected_size else "partial"

        match_id_counts: dict[str, int] = {}
        for row in rows:
            match_id = str(row.get("source_match_id", ""))
            match_id_counts[match_id] = match_id_counts.get(match_id, 0) + 1
        duplicate_source_match_ids = sorted(set([k for k, v in match_id_counts.items() if k and v > 1] + getattr(self, "_last_duplicate_source_match_ids", [])))

        strategy = next((str(r.get("strategy", "")) for r in rows if r.get("strategy")), "unknown")
        persist_allowed = coverage_status != "partial"

        return DiscoveryResult(
            competition=competition_slug,
            season_key=season_key,
            strategy=strategy,
            targets_by_source_match_id=discovered,
            targets_by_round=targets_by_round,
            missing_rounds=missing_rounds,
            duplicate_source_match_ids=duplicate_source_match_ids,
            unstable_rounds=sorted(set([r for r in unstable_rounds if r]), key=self._round_sort_key),
            coverage_status=coverage_status,
            expected_matches=expected_matches,
            persist_allowed=persist_allowed,
        )

    def _discover_by_rounds(self, *, competition_slug: str, season_key: str, competition_url: str) -> dict[str, dict[str, str]]:
        discovered: dict[str, dict[str, str]] = {}
        try:
            html = self.http_client.get(competition_url)
        except ScrapeBlockedError:
            return discovered
        parsed = self.competition_parser.parse(html)
        rounds = parsed.get("available_rounds", [])
        pages = [competition_url]
        pages.extend(f"{competition_url}/{str(round_label).strip()}" for round_label in rounds if str(round_label).strip())
        for page_url in pages:
            page = self.competition_parser.parse(self.http_client.get(page_url))
            requested_round = self._extract_requested_round_from_page_url(page_url) or str(page.get("selected_round") or "unknown")
            for match in page.get("matches", []):
                source_match_id = str(match.get("source_match_id", "")).strip()
                relative_url = str(match.get("url", "")).strip()
                if not source_match_id or not relative_url or source_match_id in discovered:
                    continue
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": self._canonical_url(relative_url), "source_competition_slug": competition_slug, "season_key": season_key, "round_label": self._normalize_round_label(requested_round), "strategy": "competition_rounds_http", "source_page": page_url}
        return discovered

    def _discover_by_browser(self, competition_slug: str, season_key: str, competition_url: str, year: int, debug: bool = False) -> dict[str, dict[str, str]]:
        if not self.browser_renderer:
            return {}
        parser_matches_by_round: dict[str, int] = {}
        unstable_rounds_all: set[str] = set()
        duplicate_source_match_ids: set[str] = set()
        per_pass_rounds: list[dict[str, list[dict[str, str]]]] = []
        rounds_attempted = 0

        for _ in range(max(1, int(self.browser_max_passes))):
            if hasattr(self.browser_renderer, "discover_rounds"):
                rendered = self.browser_renderer.discover_rounds(url=competition_url, competition=competition_slug, year=year)
            else:
                rendered = [{"round_label": label, "matches": [], "html": html} for label, html in self.browser_renderer.render_round_pages(url=competition_url, competition=competition_slug, year=year)]

            pass_rounds: dict[str, list[dict[str, str]]] = {}
            seen_in_pass: set[str] = set()
            for round_result in rendered:
                rounds_attempted += 1
                round_label_raw = str(round_result.get("requested_round") or round_result.get("round_label", ""))
                round_label = self._normalize_round_label(round_label_raw)
                diagnostics = round_result.get("diagnostics", {}) if isinstance(round_result, dict) else {}
                if isinstance(diagnostics, dict) and diagnostics.get("status_reason") not in (None, "ok"):
                    unstable_rounds_all.add(round_label)
                    continue
                round_matches = list(round_result.get("matches", []))
                if not round_matches and round_result.get("html"):
                    page = self.competition_parser.parse(str(round_result.get("html")))
                    round_matches = list(page.get("matches", []))
                parser_matches_by_round[round_label] = len(round_matches)
                for match in round_matches:
                    source_match_id = str(match.get("source_match_id", "")).strip()
                    relative_url = str(match.get("url", "")).strip()
                    if not source_match_id or not relative_url:
                        continue
                    competition_name = str(match.get("competition_name", "")).strip()
                    if competition_name and not self._is_competition_match(competition_slug, competition_name):
                        continue
                    if source_match_id in seen_in_pass:
                        duplicate_source_match_ids.add(source_match_id)
                        continue
                    seen_in_pass.add(source_match_id)
                    pass_rounds.setdefault(round_label, []).append({
                        "source_match_id": source_match_id,
                        "url": self._canonical_url(relative_url),
                        "source_competition_slug": competition_slug,
                        "season_key": season_key,
                        "round_label": round_label,
                        "strategy": "competition_rounds_browser",
                        "source_page": competition_url,
                    })
            per_pass_rounds.append(pass_rounds)

        consolidated_rounds: dict[str, list[dict[str, str]]] = {}
        for pass_rounds in per_pass_rounds:
            for round_label, matches in pass_rounds.items():
                is_valid = len(matches) == self.liga_mx_matches_per_round if competition_slug in {"clausura_mexico", "apertura_mexico"} else bool(matches)
                if not is_valid:
                    unstable_rounds_all.add(round_label)
                    continue
                if round_label not in consolidated_rounds or len(matches) > len(consolidated_rounds[round_label]):
                    consolidated_rounds[round_label] = matches

        discovered: dict[str, dict[str, str]] = {}
        id_to_round: dict[str, str] = {}
        for round_label in sorted(consolidated_rounds.keys(), key=self._round_sort_key):
            for match in consolidated_rounds[round_label]:
                source_match_id = match["source_match_id"]
                previous_round = id_to_round.get(source_match_id)
                if previous_round and previous_round != round_label:
                    duplicate_source_match_ids.add(source_match_id)
                    unstable_rounds_all.add(previous_round)
                    unstable_rounds_all.add(round_label)
                    continue
                id_to_round[source_match_id] = round_label
                discovered[source_match_id] = match

        self._last_rounds_attempted = rounds_attempted
        self._last_unstable_rounds = sorted(set([r for r in unstable_rounds_all if r]), key=self._round_sort_key)
        self._last_duplicate_source_match_ids = sorted([i for i in duplicate_source_match_ids if i])
        if debug:
            base = Path("data/snapshots/errors")
            base.mkdir(parents=True, exist_ok=True)
            summary_path = base / f"mx_season_{competition_slug}_{year}_summary.json"
            initial_html = base / f"mx_season_{competition_slug}_{year}_initial.html"
            after_load_html = base / f"mx_season_{competition_slug}_{year}_after_load.html"
            after_cookie_html = base / f"mx_season_{competition_slug}_{year}_after_cookie.html"
            screenshot = base / f"mx_season_{competition_slug}_{year}_screenshot.png"
            summary_path.write_text(json.dumps({
                "requested_url": competition_url,
                "final_url": competition_url,
                "response_status": None,
                "title": None,
                "html_length": 0,
                "body_text_length": 0,
                "has_round_select": None,
                "has_json_matches": None,
                "match_anchor_count_global": sum(parser_matches_by_round.values()),
                "match_anchor_count_scoped": len(discovered),
                "scope_candidates_found": rounds_attempted,
                "round_options_found": rounds_attempted,
                "rounds_attempted": rounds_attempted,
                "rounds_yielded": len(parser_matches_by_round),
                "parser_matches_by_round": parser_matches_by_round,
                "blocked_domains": [],
                "external_navigation_events": [],
                "initial_html": str(initial_html),
                "after_load_html": str(after_load_html),
                "after_cookie_html": str(after_cookie_html),
                "screenshot": str(screenshot),
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        return discovered

    @staticmethod
    def _canonical_url(url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        if url.startswith("//"):
            return f"https:{url}"
        return f"https://es.besoccer.com{url}"

    @staticmethod
    def _is_competition_match(competition_slug: str, competition_name: str) -> bool:
        name = competition_name.lower()
        expected = {"clausura_mexico": "liga mx - clausura", "apertura_mexico": "liga mx - apertura"}
        token = expected.get(competition_slug)
        return True if not token else token in name

    @staticmethod
    def _normalize_round_label(label: str) -> str:
        text = (label or "").strip().upper()
        match = re.search(r"(\d+)", text)
        if match:
            return f"JORNADA{int(match.group(1))}"
        return text

    @staticmethod
    def _round_sort_key(label: str) -> tuple[int, str]:
        m = re.search(r"(\d+)", label)
        return (int(m.group(1)) if m else 9999, label)

    @staticmethod
    def _extract_requested_round_from_page_url(page_url: str) -> str | None:
        match = re.search(r"/(\d+)\s*$", str(page_url).strip())
        if not match:
            return None
        return f"JORNADA{int(match.group(1))}"

    def _should_fallback(self, discovered: dict[str, dict[str, str]]) -> bool:
        return not discovered

    def _discover_by_teams(self, *, competition_slug: str, year: int, season_key: str, max_teams: int | None) -> dict[str, dict[str, str]]:
        config = get_league_config(competition_slug)
        team_slugs = list(config.get("team_slugs", []))
        if max_teams is not None:
            team_slugs = team_slugs[:max_teams]
        discovered: dict[str, dict[str, str]] = {}
        for team_slug in team_slugs:
            rows = self.team_use_case.execute(competition_slug=competition_slug, year=year, team_slug=str(team_slug), dry_run=True, persist=False)
            for row in rows:
                source_match_id = row["source_match_id"]
                if source_match_id in discovered:
                    continue
                discovered[source_match_id] = {"source_match_id": source_match_id, "url": row["url"], "source_competition_slug": competition_slug, "season_key": season_key, "round_label": "team-fallback", "strategy": "team_matches_fallback", "source_page": f"https://es.besoccer.com/equipo/partidos/{team_slug}/{year}"}
        return discovered
