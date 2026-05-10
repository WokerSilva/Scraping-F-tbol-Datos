from besoccer_scraper.cli.app import build_parser


def test_parser_accepts_db_check():
    parser = build_parser()
    args = parser.parse_args(["db", "check"])
    assert args.command == "db"
    assert args.action == "check"
