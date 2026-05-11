from besoccer_scraper.cli.app import build_parser


def test_inspect_targets_command_exists():
    args = build_parser().parse_args(["inspect", "targets", "--competition", "clausura_mexico", "--year", "2026"])
    assert args.inspect_mode == "targets"
