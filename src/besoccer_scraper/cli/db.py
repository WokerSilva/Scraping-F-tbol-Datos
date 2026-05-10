from __future__ import annotations

from besoccer_scraper.application.db_services import DatabaseService


def run_db_command(container: object, action: str) -> str:
    service = DatabaseService(container.db.engine)

    if action == "check":
        report = service.check_report(
            database_url=container.settings.database_url,
            source=container.settings.database_source,
        )
        return "\n".join(f"{key}={value}" for key, value in report.items())
    if action == "migrate":
        executed = service.migrate()
        return f"applied={','.join(executed) if executed else 'none'}"
    if action == "status":
        state = service.status()
        formatted = ", ".join(f"{v}:{s}" for v, s in state.items())
        return formatted or "no-migrations"
    raise ValueError(f"Unknown db action: {action}")
