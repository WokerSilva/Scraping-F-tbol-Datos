import subprocess
import sys
from types import SimpleNamespace


def test_cli_module_import_does_not_require_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    from besoccer_scraper.cli.app import main  # noqa: F401


def test_cli_help_works_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env = dict(**__import__("os").environ, PYTHONPATH="src")
    result = subprocess.run(
        [sys.executable, "-m", "besoccer_scraper.main", "--help"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


def test_cli_db_check_alias(monkeypatch):
    from besoccer_scraper.cli import app

    monkeypatch.setattr(app, "build_parser", app.build_parser)

    def fake_build_container(_args):
        return SimpleNamespace(db=SimpleNamespace(engine=object()))

    def fake_run_db_command(_container, action):
        return action

    monkeypatch.setitem(sys.modules, "besoccer_scraper.bootstrap", SimpleNamespace(build_container=fake_build_container))
    monkeypatch.setitem(sys.modules, "besoccer_scraper.cli.db", SimpleNamespace(run_db_command=fake_run_db_command))

    assert app.main(["db-check"]) == "check"
