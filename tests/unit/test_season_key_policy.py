from besoccer_scraper.domain.services import build_season_key


def test_season_key_policy_clausura_mexico() -> None:
    assert build_season_key("clausura_mexico", 2026) == "clausura-2026"


def test_season_key_policy_apertura_mexico() -> None:
    assert build_season_key("apertura_mexico", 2025) == "apertura-2025"


def test_season_key_policy_generic_competition_slug() -> None:
    assert build_season_key("liga_mx", 2025) == "liga_mx-2025"
