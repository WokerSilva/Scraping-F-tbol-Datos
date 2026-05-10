from __future__ import annotations

import argparse

from besoccer_scraper.bootstrap import build_container
from besoccer_scraper.cli.audit import run_audit
from besoccer_scraper.cli.db import run_db_command
from besoccer_scraper.cli.discover import run_discover
from besoccer_scraper.cli.pipeline import run_pipeline
from besoccer_scraper.cli.scrape import run_scrape


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="besoccer-scraper")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--http-timeout-seconds", type=float, default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", default=None)
    parser.add_argument("--log-level", default=None)

    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("db")
    db.add_argument("action", choices=["check", "migrate", "status"], default="status", nargs="?")

    discover = sub.add_parser("discover")
    discover.add_argument("--source-url", required=True)

    scrape = sub.add_parser("scrape")
    scrape.add_argument("--competition-id", required=True)
    scrape.add_argument("--source-url", required=True)

    audit = sub.add_parser("audit")
    audit.add_argument("--message", required=True)

    pipeline = sub.add_parser("pipeline")
    pipeline.add_argument("--discover-url", required=True)
    pipeline.add_argument("--competition-id", required=True)
    pipeline.add_argument("--scrape-url", required=True)
    return parser


def main(argv: list[str] | None = None) -> object:
    parser = build_parser()
    args = parser.parse_args(argv)
    container = build_container(args)

    if args.command == "db":
        return run_db_command(container, args.action)
    if args.command == "discover":
        return run_discover(container, args.source_url)
    if args.command == "scrape":
        return run_scrape(container, args.competition_id, args.source_url)
    if args.command == "audit":
        return run_audit(container, args.message)
    if args.command == "pipeline":
        return run_pipeline(container, args.discover_url, args.competition_id, args.scrape_url)
    raise ValueError(f"Unknown command: {args.command}")
