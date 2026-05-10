from argparse import Namespace
from types import SimpleNamespace

import pytest

pytest.importorskip("sqlalchemy")

from besoccer_scraper.cli.db import run_db_command
from besoccer_scraper.config.settings import load_settings
from besoccer_scraper.infrastructure.db.connection import sanitize_database_dsn


def _base_args(**kwargs):
    defaults = {
        "database_url": None,
        "app_env": None,
        "log_level": None,
        "active_leagues": None,
        "db_ssl_mode": None,
        "request_timeout_seconds": None,
        "user_agent": None,
        "max_retries": None,
        "dry_run": None,
    }
    defaults.update(kwargs)
    return Namespace(**defaults)


def test_db_check_output_uses_env_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:realpass@railway.up.railway.app:5432/futbol")
    settings = load_settings(_base_args())

    container = SimpleNamespace(settings=settings, db=SimpleNamespace(engine=object()))

    def fake_check_report(self, *, database_url, source):
        assert source == "env:DATABASE_URL"
        assert database_url == settings.database_url
        return {
            "provider": "postgresql",
            "database": "futbol",
            "host_masked": "ra***.up.railway.app",
            "sql_dir": "/tmp/sql/postgres",
            "migrations_applied": "2",
            "select_1": "ok",
            "source": source,
        }

    monkeypatch.setattr("besoccer_scraper.application.db_services.DatabaseService.check_report", fake_check_report)
    output = run_db_command(container, "check")

    assert "source=env:DATABASE_URL" in output
    assert "host_masked=ra***.up.railway.app" in output
    assert "realpass" not in output


def test_db_check_output_uses_cli_database_url_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:envpass@env.host:5432/envdb")
    cli_url = "postgresql://app:clipass@railway.up.railway.app:5432/clidb"
    settings = load_settings(_base_args(database_url=cli_url))

    container = SimpleNamespace(settings=settings, db=SimpleNamespace(engine=object()))

    def fake_check_report(self, *, database_url, source):
        assert source == "cli"
        assert database_url.endswith("/clidb")
        return {
            "provider": "postgresql",
            "database": "clidb",
            "host_masked": "ra***.up.railway.app",
            "sql_dir": "/tmp/sql/postgres",
            "migrations_applied": "3",
            "select_1": "ok",
            "source": source,
        }

    monkeypatch.setattr("besoccer_scraper.application.db_services.DatabaseService.check_report", fake_check_report)
    output = run_db_command(container, "check")

    assert "source=cli" in output
    assert "clipass" not in output
    assert "@" not in output


def test_sanitize_database_dsn_hides_sensitive_data():
    dsn = "postgresql://app:supersecret@railway.up.railway.app:5432/futbol?sslmode=require&password=bad"
    sanitized = sanitize_database_dsn(dsn)
    assert sanitized["provider"] == "postgresql"
    assert sanitized["database"] == "futbol"
    assert sanitized["host_masked"] == "ra***.up.railway.app"
    assert "supersecret" not in str(sanitized)
