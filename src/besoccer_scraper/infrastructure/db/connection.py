from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class DatabaseFactories:
    engine: Engine
    session_factory: sessionmaker[Session]


def normalize_database_url(database_url: str) -> str:
    """Normalize SQLAlchemy URL for psycopg driver."""
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return database_url


def build_database_factories(database_url: str) -> DatabaseFactories:
    normalized_url = normalize_database_url(database_url)
    engine = create_engine(normalized_url, future=True, pool_pre_ping=True)
    return DatabaseFactories(
        engine=engine,
        session_factory=sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True),
    )


def database_healthcheck(engine: Engine) -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
