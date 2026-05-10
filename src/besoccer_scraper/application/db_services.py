from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine

from besoccer_scraper.infrastructure.db.connection import database_healthcheck
from besoccer_scraper.infrastructure.db.migrations import MigrationRunner


@dataclass
class DatabaseService:
    engine: Engine

    def check(self) -> bool:
        return database_healthcheck(self.engine)

    def migrate(self) -> list[str]:
        return MigrationRunner(self.engine).migrate()

    def status(self) -> dict[str, str]:
        return MigrationRunner(self.engine).status()
