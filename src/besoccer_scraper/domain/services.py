from __future__ import annotations


def build_season_key(competition_slug: str, year: int) -> str:
    if competition_slug == "clausura_mexico":
        return f"clausura-{year}"
    if competition_slug == "apertura_mexico":
        return f"apertura-{year}"
    return f"{competition_slug}-{year}"
