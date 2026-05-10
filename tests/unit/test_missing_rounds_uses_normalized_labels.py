from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


def test_missing_rounds_uses_normalized_labels() -> None:
    detected = {DiscoverMxSeasonUseCase._normalize_round_label(x) for x in ["Jornada 1", "JORNADA2", "Jor. 3"]}
    missing = [f"JORNADA{i}" for i in range(1, 5) if f"JORNADA{i}" not in detected]
    assert missing == ["JORNADA4"]
