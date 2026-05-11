from besoccer_scraper.cli.app import build_parser


def test_scrape_match_command_uses_competition_slug():
    args = build_parser().parse_args(["scrape", "match", "--url", "https://x", "--competition-slug", "clausura_mexico"])
    assert args.scrape_mode == "match"
    assert args.competition_slug == "clausura_mexico"
