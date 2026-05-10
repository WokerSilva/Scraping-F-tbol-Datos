from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "sql" / "postgres"


class MigrationRunner:
    def __init__(self, engine: Engine, migrations_dir: Path = MIGRATIONS_DIR) -> None:
        self.engine = engine
        self.migrations_dir = migrations_dir

    def _ensure_version_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
        with self.engine.begin() as conn:
            conn.execute(text(sql))

    def available_versions(self) -> list[str]:
        return sorted(path.stem.split("_", 1)[0] for path in self.migrations_dir.glob("*.sql"))

    def applied_versions(self) -> set[str]:
        self._ensure_version_table()
        with self.engine.connect() as conn:
            rows = conn.execute(text("SELECT version FROM schema_migrations")).scalars().all()
        return set(rows)

    def status(self) -> dict[str, str]:
        applied = self.applied_versions()
        return {version: ("applied" if version in applied else "pending") for version in self.available_versions()}

    def migrate(self) -> list[str]:
        self._ensure_version_table()
        applied = self.applied_versions()
        executed: list[str] = []
        for path in sorted(self.migrations_dir.glob("*.sql")):
            version = path.stem.split("_", 1)[0]
            if version in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            with self.engine.begin() as conn:
                if sql.strip():
                    conn.execute(text(sql))
                conn.execute(
                    text("INSERT INTO schema_migrations(version) VALUES (:version)"),
                    {"version": version},
                )
            executed.append(version)
            applied.add(version)
        return executed
