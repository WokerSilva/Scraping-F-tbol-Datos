from besoccer_scraper.infrastructure.parsers.competition_parser import CompetitionParser


def _mx_rendered_html() -> str:
    options = "\n".join(
        f'<option{" selected" if idx == 17 else ""}>JORNADA{idx}</option>'
        for idx in range(1, 18)
    )
    matches = """
    <main>
      <div id="mod_mainCompetitionRounds" class="panel-body match-list-new comp-matches">
        <article>
          <a id="match-2022305526" href="https://es.besoccer.com/partido/necaxa/guadalajara/2022305526" data-cy="match">Ver partido</a>
          <span class="middle-info">Liga MX - Clausura</span>
          <span class="team_left"><span class="name">Necaxa</span></span>
          <span class="team_right"><span class="name">Chivas Guadalajara</span></span>
          <span class="r1">0</span><span class="r2">1</span>
          <span class="match-status-label">FT</span>
        </article>
        <article><a class="match-link" href="/partido/club-america/pumas-unam/2022305527">Ver partido</a><span class="team_left"><span class="name">Club América</span></span><span class="team_right"><span class="name">Pumas UNAM</span></span><span class="r1">2</span><span class="r2">0</span></article>
        <article><a data-cy="match" href="/partido/cruz-azul/atlas/2022305528">Ver partido</a><span class="team_left"><span class="name">Cruz Azul</span></span><span class="team_right"><span class="name">Atlas</span></span><span class="r1">1</span><span class="r2">1</span></article>
        <article><a href="/partido/tigres-uanl/leon/2022305529">Ver partido</a><span class="team_left"><span class="name">Tigres UANL</span></span><span class="team_right"><span class="name">León</span></span><span class="r1">3</span><span class="r2">2</span></article>
        <article><a href="/partido/monterrey/santos-laguna/2022305530">Ver partido</a><span class="team_left"><span class="name">Monterrey</span></span><span class="team_right"><span class="name">Santos Laguna</span></span><span class="r1">1</span><span class="r2">0</span></article>
        <article><a href="/partido/pachuca/toluca/2022305531">Ver partido</a><span class="team_left"><span class="name">Pachuca</span></span><span class="team_right"><span class="name">Toluca</span></span><span class="r1">0</span><span class="r2">0</span></article>
        <article><a href="/partido/mazatlan/fc-juarez/2022305532">Ver partido</a><span class="team_left"><span class="name">Mazatlán</span></span><span class="team_right"><span class="name">FC Juárez</span></span><span class="r1">2</span><span class="r2">1</span></article>
        <article><a href="/partido/tijuana/puebla/2022305533">Ver partido</a><span class="team_left"><span class="name">Tijuana</span></span><span class="team_right"><span class="name">Puebla</span></span><span class="r1">1</span><span class="r2">2</span></article>
      </div>
    </main>
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
    assert first.url == "https://es.besoccer.com/partido/necaxa/guadalajara/2022305526"
    assert len(parsed.matches) >= 8
    assert first.round_label == "JORNADA17"
    assert first.home_team_name == "Necaxa"
    assert first.away_team_name == "Chivas Guadalajara"
    assert first.home_score == 0
    assert first.away_score == 1
