from __future__ import annotations

from besoccer_scraper.shared.exceptions import ScrapeBlockedError


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
            )
        except ScrapeBlockedError as exc:
            if exc.status_code == 406:
                print("BeSoccer rechazó la petición HTTP simple (406). Reintenta con browser fallback o USE_BROWSER_FALLBACK=true.")
            else:
                print(f"Discovery bloqueado por BeSoccer (status={exc.status_code}).")
            return 2
        return len(rows)

    return container.discover_use_case.execute(args.source_url)
