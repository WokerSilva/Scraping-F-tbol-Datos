from __future__ import annotations

import json
from pathlib import Path
import re

from besoccer_scraper.shared.exceptions import HttpFetchError, ScrapeBlockedError


def run_discover(container: object, args: object) -> int:
    if args.discover_mode == "mx-team":
        rows = container.discover_mx_team_use_case.execute(
            competition_slug=args.competition,
            year=args.year,
            team_slug=args.team,
            dry_run=args.dry_run,
            print_urls=args.print_urls,
            persist=False,
        )
        return len(rows)

    if args.discover_mode == "mx-season":
        dry_run = args.dry_run or not args.persist
        try:
            rows = container.discover_mx_season_use_case.execute(
                competition_slug=args.competition,
                year=args.year,
                max_teams=args.max_teams,
                dry_run=dry_run,
                persist=args.persist,
                print_urls=args.print_urls,
                browser=args.browser,
                fallback_to_teams=(args.fallback_teams if args.fallback_teams is not None else (not dry_run)),
                debug=getattr(args, "debug", False),
                sample_size=getattr(args, "sample_size", 3),
                allow_partial=getattr(args, "allow_partial", False),
            )
        except ScrapeBlockedError as exc:
            if exc.status_code == 406:
                print("BeSoccer rechazó la petición HTTP simple (406). Reintenta con browser fallback o USE_BROWSER_FALLBACK=true.")
            else:
                print(f"Discovery bloqueado por BeSoccer (status={exc.status_code}).")
            return 2
        except HttpFetchError as exc:
            message = str(exc)
            if "External navigation blocked/detected:" in message:
                external_url = message.split("External navigation blocked/detected:", 1)[1].strip()
                print("Se bloqueó navegación externa durante render BeSoccer.")
                print(f"URL externa: {external_url}")
                print("Reintenta; si persiste, revisar network log.")
            else:
                print(message)
            if getattr(args, "debug", False):
                marker = "Debug snapshot: "
                if marker in message:
                    match = re.search(r"Debug snapshot:\s*([^\s]+\.json)", message)
                    meta_path = match.group(1) if match else ""
                    path = Path(meta_path)
                    if path.exists():
                        meta = json.loads(path.read_text(encoding="utf-8"))
                        print(f"debug_html={meta.get('html_path')}")
                        print(f"debug_screenshot={meta.get('screenshot_path')}")
                        print(f"response_status={meta.get('response_status')}")
                        print(f"final_url={meta.get('final_url')}")
                        print(f"html_length={meta.get('html_length')}")
                        print(f"body_text_length={meta.get('body_text_length')}")
                        print(f"match_anchor_count={meta.get('match_anchor_count')}")
            return 2
        return len(rows)

    return container.discover_use_case.execute(args.source_url)
