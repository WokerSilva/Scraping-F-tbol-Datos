from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.engine import Engine
from sqlalchemy import text

from besoccer_scraper.infrastructure.db.connection import database_healthcheck, sanitize_database_dsn
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

    def check_report(self, *, database_url: str, source: str) -> dict[str, str]:
        dsn = sanitize_database_dsn(database_url)
        status = self.status()
        select_1 = "ok" if self.check() else "fail"
        sql_dir = str(Path(MigrationRunner(self.engine).migrations_dir))
        migrations_applied = str(sum(1 for value in status.values() if value == "applied"))
        return {
            "provider": dsn["provider"],
            "database": dsn["database"],
            "host_masked": dsn["host_masked"],
            "sql_dir": sql_dir,
            "migrations_applied": migrations_applied,
            "select_1": select_1,
            "source": source,
        }

    def schema_report(self) -> dict[str, list[str]]:
        tables = ["scrape_targets", "raw_pages", "matches", "job_runs", "job_logs", "schema_migrations"]
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = ANY(:tables)
                    ORDER BY table_name, ordinal_position
                    """
                ),
                {"tables": tables},
            ).mappings()
            out: dict[str, list[str]] = {table: [] for table in tables}
            for row in rows:
                out[str(row["table_name"])].append(str(row["column_name"]))
            return out
