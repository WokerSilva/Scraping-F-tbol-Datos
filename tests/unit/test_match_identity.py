from besoccer_scraper.shared.text import extract_source_match_id


def test_extract_source_match_id_from_url():
    url = "https://www.besoccer.com/match/club-america/chivas-guadalajara/202598765"
    assert extract_source_match_id(url) == "202598765"


def test_match_id_stability():
    url_a = "https://www.besoccer.com/match/a/b/20251234"
    url_b = "https://www.besoccer.com/match/x/y/20251234?foo=1"
    assert extract_source_match_id(url_a) == extract_source_match_id(url_b)
