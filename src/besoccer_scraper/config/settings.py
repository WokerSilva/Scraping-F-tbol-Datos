from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any


@dataclass(frozen=True)
class Settings:
    database_url: str
    http_timeout_seconds: float
    user_agent: str
    max_retries: int
    dry_run: bool
    log_level: str


DEFAULTS = {
    "database_url": "postgresql://postgres:postgres@localhost:5432/besoccer",
    "http_timeout_seconds": 15.0,
    "user_agent": "besoccer-scraper/1.0",
    "max_retries": 3,
    "dry_run": False,
    "log_level": "INFO",
}


def _parse_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip("\"'")
    return data


def _as_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_settings(cli_args: Namespace | None = None, *, env_file: str = ".env") -> Settings:
    cli = vars(cli_args) if cli_args is not None else {}
    env_file_values = _parse_env_file(Path(env_file))

    def pick(name: str, env_key: str) -> Any:
        if cli.get(name) is not None:
            return cli[name]
        if env_key in os.environ:
            return os.environ[env_key]
        if env_key in env_file_values:
            return env_file_values[env_key]
        return DEFAULTS[name]

    return Settings(
        database_url=str(pick("database_url", "BESOCCER_DATABASE_URL")),
        http_timeout_seconds=float(pick("http_timeout_seconds", "BESOCCER_HTTP_TIMEOUT_SECONDS")),
        user_agent=str(pick("user_agent", "BESOCCER_USER_AGENT")),
        max_retries=int(pick("max_retries", "BESOCCER_MAX_RETRIES")),
        dry_run=_as_bool(pick("dry_run", "BESOCCER_DRY_RUN"), default=DEFAULTS["dry_run"]),
        log_level=str(pick("log_level", "BESOCCER_LOG_LEVEL")).upper(),
    )
