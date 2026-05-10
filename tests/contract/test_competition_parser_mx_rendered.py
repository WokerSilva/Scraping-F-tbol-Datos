from besoccer_scraper.infrastructure.parsers.competition_parser import CompetitionParser


def _mx_rendered_html() -> str:
    options = "\n".join(
        f'<option{" selected" if idx == 17 else ""}>JORNADA{idx}</option>'
        for idx in range(1, 18)
    )
    matches = """
    <article>
      <a href="/partido/club-america/chivas-guadalajara/2022305526">Ver partido</a>
      <span data-cy="homeTeam">Club América</span>
      <span data-cy="awayTeam">Chivas Guadalajara</span>
      <span data-cy="matchStatus">2-1</span>
      <time datetime="2025-05-03T01:00:00Z"></time>
    </article>
    <article>
      <a href="https://www.besoccer.com/partido/cruz-azul/pumas-unam/2022305527?foo=1">Ver partido</a>
      <span data-cy="homeTeam">Cruz Azul</span>
      <span data-cy="awayTeam">Pumas UNAM</span>
      <span data-cy="matchStatus">0-0</span>
    </article>
    """
    return f"""
    <html>
      <head>
        <meta property="og:title" content="Liga MX - Clausura" />
      </head>
      <body>
        <select data-cy="roundSelect">{options}</select>
        {matches}
      </body>
    </html>
    """


def test_competition_parser_mx_rendered_detects_rounds_and_matches() -> None:
    parsed = CompetitionParser().parse_rendered(_mx_rendered_html())

    assert len(parsed.available_rounds) == 17
    assert parsed.selected_round == "JORNADA17"

    ids = {match.source_match_id for match in parsed.matches}
    assert "2022305526" in ids

    first = next(match for match in parsed.matches if match.source_match_id == "2022305526")
    assert first.url.startswith("/partido/")
    assert first.home_team_name == "Club América"
    assert first.away_team_name == "Chivas Guadalajara"
    assert first.score_status == "2-1"
