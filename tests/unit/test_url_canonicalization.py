from besoccer_scraper.application.discovery import DiscoverMxSeasonUseCase


def test_url_canonicalization_absolute_kept() -> None:
    url = "https://es.besoccer.com/partido/america/tigres-uanl/2026239088"
    assert DiscoverMxSeasonUseCase._canonical_url(url) == url


def test_url_canonicalization_relative_to_absolute() -> None:
    rel = "/partido/america/tigres-uanl/2026239088"
    assert DiscoverMxSeasonUseCase._canonical_url(rel) == "https://es.besoccer.com/partido/america/tigres-uanl/2026239088"
