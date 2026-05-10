class _Renderer:
    def render_round_pages(self, *, url: str, competition: str | None = None, year: int | None = None):
        return [("JORNADA1", "<html></html>")]


def test_browser_renderer_contract_accepts_competition_and_year_kwargs() -> None:
    renderer = _Renderer()
    pages = renderer.render_round_pages(
        url="https://es.besoccer.com/competicion/resultados/clausura_mexico/2026",
        competition="clausura_mexico",
        year=2026,
    )
    assert pages and pages[0][0] == "JORNADA1"
