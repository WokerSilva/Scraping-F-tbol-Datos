from __future__ import annotations


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
        rows = container.discover_mx_season_use_case.execute(
            competition_slug=args.competition,
            year=args.year,
            max_teams=args.max_teams,
            dry_run=dry_run,
            persist=args.persist,
            print_urls=args.print_urls,
        )
        return len(rows)

    return container.discover_use_case.execute(args.source_url)
