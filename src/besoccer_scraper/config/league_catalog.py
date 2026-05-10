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
