from besoccer_scraper.config.league_catalog import LEAGUE_CATALOG


def test_mx_competitions_exist():
    assert "clausura_mexico" in LEAGUE_CATALOG
    assert "apertura_mexico" in LEAGUE_CATALOG


def test_mx_policies():
    assert LEAGUE_CATALOG["clausura_mexico"]["discovery_strategy"] == "team_matches_filter"
    assert LEAGUE_CATALOG["apertura_mexico"]["season_policy"] == "short_tournament_year"
