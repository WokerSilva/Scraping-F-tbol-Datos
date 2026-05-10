from besoccer_scraper.cli.app import build_parser


def test_parser_accepts_db_check():
    parser = build_parser()
    args = parser.parse_args(["db", "check"])
    assert args.command == "db"
    assert args.action == "check"


def test_parser_accepts_audit_mx_season_and_inspect_match():
    parser = build_parser()
    args = parser.parse_args(["audit", "mx-season", "--competition", "ligamx-apertura", "--year", "2025"])
    assert args.command == "audit"
    assert args.audit_mode == "mx-season"
    assert args.year == 2025

    args2 = parser.parse_args(["inspect", "match", "--source-match-id", "12345"])
    assert args2.command == "inspect"
    assert args2.inspect_mode == "match"
    assert args2.source_match_id == "12345"
