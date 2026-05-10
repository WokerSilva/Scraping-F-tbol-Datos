from __future__ import annotations


def run_db_command(container: object) -> str:
    return f"DB ready={container.db_connection.connected}"
