from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


def test_normalize_round_label() -> None:
    assert DiscoverMxSeasonUseCase._normalize_round_label("Jornada 1") == "JORNADA1"
    assert DiscoverMxSeasonUseCase._normalize_round_label("JORNADA1") == "JORNADA1"
    assert DiscoverMxSeasonUseCase._normalize_round_label("Jor. 1") == "JORNADA1"
