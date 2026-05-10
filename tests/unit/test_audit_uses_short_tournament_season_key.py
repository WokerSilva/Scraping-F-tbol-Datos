from besoccer_scraper.application.audit import AuditMxSeasonUseCase


class Repo:
    season_key = None

    def coverage_by_competition_season(self, **kwargs):
        self.season_key = kwargs["season_key"]
        return {"targets_total": 0, "pending": 0, "in_progress": 0, "parsed": 0, "retry_scheduled": 0, "blocked": 0, "failed_permanent": 0, "matches_total": 0, "duplicates_detected": 0}


class Session:
    def execute(self, *args, **kwargs):
        class R:
            def mappings(self):
                return []
        return R()


class UoW:
    def __init__(self):
        self.scrape_targets = Repo()
        self.session = Session()


def test_audit_uses_short_tournament_key() -> None:
    uow = UoW()
    AuditMxSeasonUseCase(uow=uow).execute(competition="clausura_mexico", year=2026)
    assert uow.scrape_targets.season_key == "clausura-2026"
