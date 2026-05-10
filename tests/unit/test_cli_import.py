import subprocess
import sys


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
