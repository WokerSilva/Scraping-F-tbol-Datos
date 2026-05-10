from besoccer_scraper.domain.services import build_season_key


def test_discovery_season_key_policy() -> None:
    assert build_season_key("clausura_mexico", 2026) == "clausura-2026"
    assert build_season_key("apertura_mexico", 2025) == "apertura-2025"
