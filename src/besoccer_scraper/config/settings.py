from __future__ import annotations

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
import os
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return False


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_env: str
    log_level: str
    active_leagues: tuple[str, ...]
    db_ssl_mode: str


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: Any, default: int) -> int:
    return default if value is None or value == "" else int(value)


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(x.strip() for x in value.split(",") if x.strip())


def load_settings(cli_args: Namespace | None = None, *, env_file: str = ".env") -> Settings:
    load_dotenv(env_file, override=False)
    cli = vars(cli_args) if cli_args else {}

    def pick(cli_key: str, env_key: str, default: Any = None) -> Any:
        if cli.get(cli_key) is not None:
            return cli[cli_key]
        return os.getenv(env_key, default)

    raw_db_url = pick("database_url", "DATABASE_URL") or pick("database_url", "BESOCCER_DATABASE_URL")
    database_url = _normalize_database_url(str(raw_db_url)) if raw_db_url else ""

    return Settings(
        database_url=database_url,
        app_env=str(pick("app_env", "APP_ENV", "dev")),
        log_level=str(pick("log_level", "LOG_LEVEL", "INFO")).upper(),
        active_leagues=_split_csv(str(pick("active_leagues", "ACTIVE_LEAGUES", ""))),
        db_ssl_mode=str(pick("db_ssl_mode", "DB_SSL_MODE", "prefer")),
    )


def require_database_url(settings: Settings) -> None:
    if not settings.database_url:
        raise ValueError("DATABASE_URL no está definido. Configura .env con PostgreSQL/Railway.")
