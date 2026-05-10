from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class DatabaseFactories:
    engine: Engine
    session_factory: sessionmaker[Session]


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def with_ssl_mode(database_url: str, ssl_mode: str) -> str:
    if not ssl_mode:
        return database_url
    parts = urlsplit(database_url)
    q = dict(parse_qsl(parts.query, keep_blank_values=True))
    q.setdefault("sslmode", ssl_mode)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


def mask_database_url(database_url: str) -> str:
    parts = urlsplit(database_url)
    if "@" not in parts.netloc:
        return database_url
    creds, host = parts.netloc.rsplit("@", 1)
    user = creds.split(":", 1)[0]
    return urlunsplit((parts.scheme, f"{user}:***@{host}", parts.path, parts.query, parts.fragment))


def mask_host(host: str) -> str:
    if not host:
        return ""
    labels = host.split(".")
    first = labels[0]
    if len(first) <= 2:
        first_masked = "*" * len(first)
    else:
        first_masked = f"{first[:2]}***"
    labels[0] = first_masked
    return ".".join(labels)


def sanitize_database_dsn(database_url: str) -> dict[str, str]:
    parts = urlsplit(database_url)
    host = parts.hostname or ""
    provider = parts.scheme.split("+", 1)[0] if parts.scheme else ""
    return {
        "provider": provider,
        "database": parts.path.lstrip("/"),
        "host_masked": mask_host(host),
    }


def build_database_factories(database_url: str) -> DatabaseFactories:
    normalized_url = normalize_database_url(database_url)
    engine = create_engine(normalized_url, future=True, pool_pre_ping=True)
    return DatabaseFactories(engine=engine, session_factory=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True))


def database_healthcheck(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
