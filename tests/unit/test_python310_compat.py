"""Smoke tests for Python 3.10 import compatibility."""

from importlib import import_module

import pytest


def test_python310_import_compatibility() -> None:
    """Critical modules should import without Python 3.11-only APIs."""
    modules = (
        "besoccer_scraper.infrastructure.parsers.match_parser",
        "besoccer_scraper.bootstrap",
        "besoccer_scraper.cli.app",
    )

    for module_name in modules:
        try:
            import_module(module_name)
        except ModuleNotFoundError as exc:
            pytest.skip(f"Missing dependency in test environment: {exc.name}")
        except ImportError as exc:
            assert "cannot import name 'UTC' from 'datetime'" not in str(exc)
            raise
