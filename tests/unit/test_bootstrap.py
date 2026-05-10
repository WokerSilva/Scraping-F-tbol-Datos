from argparse import Namespace

import pytest


pytest.importorskip("sqlalchemy")

from besoccer_scraper.bootstrap import build_container


def test_build_container_uses_default_request_timeout(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    container = build_container(Namespace())
    assert container.settings.request_timeout_seconds == 30
    assert container.http_client.timeout_seconds == 30
