from __future__ import annotations


def run_audit_message(container: object, message: str) -> str:
    return container.audit_use_case.execute(message)


def run_audit_coverage(container: object, *, competition: str, season_key: str) -> dict[str, int | float | str | None]:
    return container.audit_coverage_use_case.execute(competition=competition, season_key=season_key)


def run_audit_mx_season(container: object, *, competition: str, year: int) -> dict[str, object]:
    return container.audit_mx_season_use_case.execute(competition=competition, year=year)


def inspect_match(container: object, *, source_match_id: str) -> dict[str, object] | None:
    result = container.inspect_match_use_case.execute(source_match_id=source_match_id)
    if result is None:
        return None

    return {
        "source_match_id": result.get("source_match_id"),
        "url": result.get("url"),
        "competition_slug": result.get("competition_slug"),
        "season_key": result.get("season_key"),
        "round_label": result.get("round_label"),
        "home_team": result.get("home_team"),
        "away_team": result.get("away_team"),
        "score": result.get("score"),
        "venue": result.get("venue"),
        "status": result.get("status"),
        "stats_count": result.get("stats_count"),
        "goals_count": result.get("goals_count"),
        "goals": result.get("goals", []),
        "stats_summary": result.get("stats_summary", {}),
        "metadata": result.get("metadata", {}),
    }


def inspect_targets(container: object, *, competition: str, year: int) -> dict[str, object]:
    return container.inspect_targets_use_case.execute(competition=competition, year=year)
