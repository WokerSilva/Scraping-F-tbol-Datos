from besoccer_scraper.shared.text import extract_source_match_id


def test_extract_source_match_id_from_partido_url() -> None:
    assert extract_source_match_id("https://www.besoccer.com/partido/a/b/2022305526") == "2022305526"


def test_extract_source_match_id_ignores_query_and_trailing_slash() -> None:
    url = "https://www.besoccer.com/partido/a/b/2022305526/?utm=abc"
    assert extract_source_match_id(url) == "2022305526"


def test_extract_source_match_id_returns_none_without_numeric_suffix() -> None:
    assert extract_source_match_id("https://www.besoccer.com/partido/a/b/final") is None
