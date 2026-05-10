from besoccer_scraper.infrastructure.http.client import HttpClient


def test_http_client_headers_include_user_agent_and_accept_language() -> None:
    client = HttpClient(timeout_seconds=30, user_agent="UA")
    headers = client._headers()
    assert headers["User-Agent"] == "UA"
    assert "es-MX" in headers["Accept-Language"]
