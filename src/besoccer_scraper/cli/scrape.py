from __future__ import annotations


def run_scrape(container: object, args: object) -> int:
    if args.scrape_mode == "match":
        return container.scrape_use_case.execute_match_url(
            url=args.url,
            competition_slug=args.competition_slug,
            round_label=args.round_label,
            season_key=args.season_key,
            debug_html=args.debug_html,
            target_id=args.target_id,
        )
    if args.scrape_mode == "pending-matches":
        return container.scrape_use_case.execute_pending_matches(
            competition_slug=args.competition,
            season_key=args.season_key,
            limit=args.limit,
            debug_html=args.debug_html,
        )
    if args.scrape_mode == "rescrape-matches":
        return container.scrape_use_case.execute_rescrape_matches(
            competition_slug=args.competition,
            season_key=args.season_key,
            limit=args.limit,
            source_match_id=args.source_match_id,
            debug_html=args.debug_html,
        )
    return container.scrape_use_case.execute(args.competition_id, args.source_url)
