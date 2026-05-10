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
    database_source: str
    app_env: str
    log_level: str
    request_timeout_seconds: int
    user_agent: str
    max_retries: int
    dry_run: bool
    request_delay_min_seconds: float
    request_delay_max_seconds: float
    use_browser_fallback: bool
    browser_wait_after_load_ms: int
    save_raw_pages: bool
    cache_enabled: bool
    active_leagues: tuple[str, ...]
    start_year: int
    years_back: int
    batch_size: int
    scrape_limit: int
    run_lock_enabled: bool
    run_lock_ttl_minutes: int
    db_ssl_mode: str

    @property
    def http_timeout_seconds(self) -> int:
        return self.request_timeout_seconds


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

    cli_database_url = cli.get("database_url")
    if cli_database_url is not None:
        raw_db_url = cli_database_url
        database_source = "cli"
    else:
        env_database_url = os.getenv("DATABASE_URL")
        if env_database_url:
            raw_db_url = env_database_url
            database_source = "env:DATABASE_URL"
        else:
            alt_env_database_url = os.getenv("BESOCCER_DATABASE_URL")
            raw_db_url = alt_env_database_url
            database_source = "env:BESOCCER_DATABASE_URL" if alt_env_database_url else "unset"
    database_url = _normalize_database_url(str(raw_db_url)) if raw_db_url else ""

    return Settings(
        database_url=database_url,
        database_source=database_source,
        app_env=str(pick("app_env", "APP_ENV", "dev")),
        log_level=str(pick("log_level", "LOG_LEVEL", "INFO")).upper(),
        request_timeout_seconds=_as_int(pick("request_timeout_seconds", "REQUEST_TIMEOUT_SECONDS", 30), 30),
        user_agent=str(pick("user_agent", "USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")),
        max_retries=_as_int(pick("max_retries", "MAX_RETRIES", 3), 3),
        dry_run=_as_bool(pick("dry_run", "DRY_RUN", False), False),
        request_delay_min_seconds=float(pick("request_delay_min_seconds", "REQUEST_DELAY_MIN_SECONDS", 0.0) or 0.0),
        request_delay_max_seconds=float(pick("request_delay_max_seconds", "REQUEST_DELAY_MAX_SECONDS", 0.0) or 0.0),
        use_browser_fallback=_as_bool(pick("use_browser_fallback", "USE_BROWSER_FALLBACK", True), True),
        browser_wait_after_load_ms=_as_int(pick("browser_wait_after_load_ms", "BROWSER_WAIT_AFTER_LOAD_MS", 1200), 1200),
        save_raw_pages=_as_bool(pick("save_raw_pages", "SAVE_RAW_PAGES", False), False),
        cache_enabled=_as_bool(pick("cache_enabled", "CACHE_ENABLED", False), False),
        active_leagues=_split_csv(str(pick("active_leagues", "ACTIVE_LEAGUES", ""))),
        start_year=_as_int(pick("start_year", "START_YEAR", 2020), 2020),
        years_back=_as_int(pick("years_back", "YEARS_BACK", 5), 5),
        batch_size=_as_int(pick("batch_size", "BATCH_SIZE", 100), 100),
        scrape_limit=_as_int(pick("scrape_limit", "SCRAPE_LIMIT", 0), 0),
        run_lock_enabled=_as_bool(pick("run_lock_enabled", "RUN_LOCK_ENABLED", True), True),
        run_lock_ttl_minutes=_as_int(pick("run_lock_ttl_minutes", "RUN_LOCK_TTL_MINUTES", 60), 60),
        db_ssl_mode=str(pick("db_ssl_mode", "DB_SSL_MODE", "prefer")),
    )


def require_database_url(settings: Settings) -> None:
    if not settings.database_url:
        raise ValueError("DATABASE_URL no está definido. Configura .env con PostgreSQL/Railway.")
