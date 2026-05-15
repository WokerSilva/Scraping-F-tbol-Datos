from besoccer_scraper.cli.app import build_parser


def test_discovery_require_complete_flag_exists():
    args = build_parser().parse_args([
        "discover", "mx-season",
        "--competition", "clausura_mexico",
        "--year", "2026",
        "--require-complete",
    ])
    assert args.require_complete is True
