from argparse import Namespace

from besoccer_scraper.config.settings import load_settings


def test_database_url_normalization(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    settings = load_settings()
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_active_leagues_parse(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("ACTIVE_LEAGUES", "mx, ar , br")
    settings = load_settings()
    assert settings.active_leagues == ("mx", "ar", "br")


def test_cli_precedence_over_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db1")
    args = Namespace(database_url="postgresql://u:p@localhost:5432/db2", app_env=None, log_level=None, active_leagues=None, db_ssl_mode=None)
    settings = load_settings(args)
    assert settings.database_url.endswith("/db2")
