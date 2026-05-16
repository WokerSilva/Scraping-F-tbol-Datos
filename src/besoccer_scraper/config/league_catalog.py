from __future__ import annotations

LEAGUE_CATALOG: dict[str, dict[str, object]] = {
    "clausura_mexico": {
        "competition_slug": "clausura_mexico",
        "display_name": "Liga MX Clausura",
        "country": "Mexico",
        "discovery_strategy": "team_matches_filter",
        "season_policy": "short_tournament_year",
        "split_tournament": {
            "enabled": True,
            "phase": "clausura",
            "season_key_prefix": "clausura",
            "season_key_format": "clausura-{year}",
        },
        "coverage": {
            "expected_rounds": 17,
            "expected_per_round": 9,
            "expected_matches": 153,
        },
        "team_slugs": [
            "america",
            "atlas",
            "chivas-guadalajara",
            "cruz-azul",
            "juarez",
            "leon",
            "monterrey",
            "necaxa",
            "pachuca",
            "puebla",
            "queretaro",
            "santos-laguna",
            "san-luis",
            "tigres-uanl",
            "toluca",
            "tijuana",
            "unam-pumas",
            "mazatlan-fc",
        ],
    },
    "apertura_mexico": {
        "competition_slug": "apertura_mexico",
        "display_name": "Liga MX Apertura",
        "country": "Mexico",
        "discovery_strategy": "team_matches_filter",
        "season_policy": "short_tournament_year",
        "split_tournament": {
            "enabled": True,
            "phase": "apertura",
            "season_key_prefix": "apertura",
            "season_key_format": "apertura-{year}",
        },
        "coverage": {
            "expected_rounds": 17,
            "expected_per_round": 9,
            "expected_matches": 153,
        },
        "team_slugs": [
            "america",
            "atlas",
            "chivas-guadalajara",
            "cruz-azul",
            "juarez",
            "leon",
            "monterrey",
            "necaxa",
            "pachuca",
            "puebla",
            "queretaro",
            "santos-laguna",
            "san-luis",
            "tigres-uanl",
            "toluca",
            "tijuana",
            "unam-pumas",
            "mazatlan-fc",
        ],
    },
}


def get_league_config(competition_slug: str) -> dict[str, object]:
    if competition_slug not in LEAGUE_CATALOG:
        raise KeyError(f"Competition not in catalog: {competition_slug}")
    return LEAGUE_CATALOG[competition_slug]


def get_coverage_expectations(competition_slug: str) -> dict[str, int]:
    config = get_league_config(competition_slug)
    coverage = config.get("coverage", {})
    if not isinstance(coverage, dict):
        coverage = {}
    expected_rounds = int(coverage.get("expected_rounds", 0) or 0)
    expected_per_round = int(coverage.get("expected_per_round", 0) or 0)
    expected_matches = int(coverage.get("expected_matches", 0) or 0)
    return {
        "expected_rounds": expected_rounds,
        "expected_per_round": expected_per_round,
        "expected_matches": expected_matches,
    }
