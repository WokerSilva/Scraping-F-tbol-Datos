from __future__ import annotations


def run_audit_message(container: object, message: str) -> str:
    return container.audit_use_case.execute(message)


def run_audit_coverage(container: object, *, competition: str, season_key: str) -> dict[str, int | float | str | None]:
    return container.audit_coverage_use_case.execute(competition=competition, season_key=season_key)
