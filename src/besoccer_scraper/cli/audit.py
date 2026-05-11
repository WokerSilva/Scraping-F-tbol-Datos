from __future__ import annotations


def run_audit_message(container: object, message: str) -> str:
    return container.audit_use_case.execute(message)


def run_audit_coverage(container: object, *, competition: str, season_key: str) -> dict[str, int | float | str | None]:
    return container.audit_coverage_use_case.execute(competition=competition, season_key=season_key)


def run_audit_mx_season(container: object, *, competition: str, year: int) -> dict[str, object]:
    return container.audit_mx_season_use_case.execute(competition=competition, year=year)


def inspect_match(container: object, *, source_match_id: str) -> dict[str, object] | None:
    return container.inspect_match_use_case.execute(source_match_id=source_match_id)


def inspect_targets(container: object, *, competition: str, year: int) -> dict[str, object]:
    return container.inspect_targets_use_case.execute(competition=competition, year=year)
