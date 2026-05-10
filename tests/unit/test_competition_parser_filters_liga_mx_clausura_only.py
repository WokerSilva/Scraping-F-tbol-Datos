from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


def test_competition_filter_liga_mx_clausura_only() -> None:
    assert DiscoverMxSeasonUseCase._is_competition_match("clausura_mexico", "Liga MX - Clausura")
    assert not DiscoverMxSeasonUseCase._is_competition_match("clausura_mexico", "LaLiga")
