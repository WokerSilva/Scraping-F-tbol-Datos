from __future__ import annotations

import argparse
import sys


ALIASES = {"db-check": ["db", "check"], "db-migrate": ["db", "migrate"], "db-status": ["db", "status"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="besoccer-scraper")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--request-timeout-seconds", "--http-timeout-seconds", dest="request_timeout_seconds", type=float, default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--log-level", default=None)

    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("db")
    db.add_argument("action", choices=["check", "migrate", "status"], default="status", nargs="?")

    discover = sub.add_parser("discover")
    discover_sub = discover.add_subparsers(dest="discover_mode")

    discover_default = discover_sub.add_parser("default")
    discover_default.set_defaults(discover_mode="default")
    discover_default.add_argument("--source-url", required=True)

    mx_team = discover_sub.add_parser("mx-team")
    mx_team.set_defaults(discover_mode="mx-team")
    mx_team.add_argument("--competition", required=True)
    mx_team.add_argument("--year", type=int, required=True)
    mx_team.add_argument("--team", required=True)
    mx_team.add_argument("--dry-run", action="store_true", default=False)
    mx_team.add_argument("--print-urls", action="store_true", default=False)

    mx_season = discover_sub.add_parser("mx-season")
    mx_season.set_defaults(discover_mode="mx-season")
    mx_season.add_argument("--competition", required=True)
    mx_season.add_argument("--year", type=int, required=True)
    mx_season.add_argument("--max-teams", type=int, default=None)
    mx_season.add_argument("--dry-run", action="store_true", default=False)
    mx_season.add_argument("--persist", action="store_true", default=False)
    mx_season.add_argument("--print-urls", action="store_true", default=False)
    mx_season.add_argument("--browser", dest="browser", action="store_true", default=None)
    mx_season.add_argument("--no-browser", dest="browser", action="store_false")

    scrape = sub.add_parser("scrape")
    scrape_sub = scrape.add_subparsers(dest="scrape_mode")
    scrape_default = scrape_sub.add_parser("default")
    scrape_default.set_defaults(scrape_mode="default")
    scrape_default.add_argument("--competition-id", required=True)
    scrape_default.add_argument("--source-url", required=True)
    scrape_match = scrape_sub.add_parser("match")
    scrape_match.set_defaults(scrape_mode="match")
    scrape_match.add_argument("--url", required=True)
    scrape_match.add_argument("--competition-slug", required=True)
    scrape_match.add_argument("--round-label", default=None)
    scrape_match.add_argument("--target-id", type=int, default=None)
    scrape_match.add_argument("--debug-html", action="store_true", default=False)
    scrape_pending = scrape_sub.add_parser("pending-matches")
    scrape_pending.set_defaults(scrape_mode="pending-matches")
    scrape_pending.add_argument("--competition", required=True)
    scrape_pending.add_argument("--season-key", required=True)
    scrape_pending.add_argument("--limit", type=int, default=20)
    scrape_pending.add_argument("--debug-html", action="store_true", default=False)

    audit = sub.add_parser("audit")
    audit_sub = audit.add_subparsers(dest="audit_mode", required=True)

    audit_message = audit_sub.add_parser("message")
    audit_message.set_defaults(audit_mode="message")
    audit_message.add_argument("--message", required=True)

    audit_coverage = audit_sub.add_parser("coverage")
    audit_coverage.set_defaults(audit_mode="coverage")
    audit_coverage.add_argument("--competition", required=True)
    audit_coverage.add_argument("--season-key", required=True)

    audit_mx_season = audit_sub.add_parser("mx-season")
    audit_mx_season.set_defaults(audit_mode="mx-season")
    audit_mx_season.add_argument("--competition", required=True)
    audit_mx_season.add_argument("--year", type=int, required=True)

    inspect = sub.add_parser("inspect")
    inspect_sub = inspect.add_subparsers(dest="inspect_mode", required=True)
    inspect_match = inspect_sub.add_parser("match")
    inspect_match.set_defaults(inspect_mode="match")
    inspect_match.add_argument("--source-match-id", required=True)

    pipeline = sub.add_parser("pipeline")
    pipeline.add_argument("--discover-url", required=True)
    pipeline.add_argument("--competition-id", required=True)
    pipeline.add_argument("--scrape-url", required=True)
    return parser


def main(argv: list[str] | None = None) -> object:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ALIASES:
        argv = ALIASES[argv[0]] + argv[1:]
    args = parser.parse_args(argv)

    if args.command == "db":
        from besoccer_scraper.bootstrap import build_container
        from besoccer_scraper.cli.db import run_db_command

        container = build_container(args)
        return run_db_command(container, args.action)
    if args.command == "discover":
        from besoccer_scraper.bootstrap import build_container
        from besoccer_scraper.cli.discover import run_discover

        container = build_container(args)
        return run_discover(container, args)
    if args.command == "scrape":
        from besoccer_scraper.bootstrap import build_container
        from besoccer_scraper.cli.scrape import run_scrape

        container = build_container(args)
        return run_scrape(container, args)
    if args.command == "audit":
        from besoccer_scraper.bootstrap import build_container
        from besoccer_scraper.cli.audit import run_audit_coverage, run_audit_message, run_audit_mx_season

        container = build_container(args)
        if args.audit_mode == "message":
            return run_audit_message(container, args.message)
        if args.audit_mode == "coverage":
            return run_audit_coverage(container, competition=args.competition, season_key=args.season_key)
        if args.audit_mode == "mx-season":
            return run_audit_mx_season(container, competition=args.competition, year=args.year)
        raise ValueError(f"Unknown audit mode: {args.audit_mode}")
    if args.command == "inspect":
        from besoccer_scraper.bootstrap import build_container
        from besoccer_scraper.cli.audit import inspect_match

        container = build_container(args)
        if args.inspect_mode == "match":
            return inspect_match(container, source_match_id=args.source_match_id)
        raise ValueError(f"Unknown inspect mode: {args.inspect_mode}")
    if args.command == "pipeline":
        from besoccer_scraper.bootstrap import build_container
        from besoccer_scraper.cli.pipeline import run_pipeline

        container = build_container(args)
        return run_pipeline(container, args.discover_url, args.competition_id, args.scrape_url)
    raise ValueError(f"Unknown command: {args.command}")
