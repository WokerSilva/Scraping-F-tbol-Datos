from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


def test_discovery_output_sorted_by_round() -> None:
    labels = ["JORNADA11", "JORNADA2", "JORNADA1"]
    ordered = sorted(labels, key=DiscoverMxSeasonUseCase._round_sort_key)
    assert ordered == ["JORNADA1", "JORNADA2", "JORNADA11"]
