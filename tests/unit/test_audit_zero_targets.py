from besoccer_scraper.application.audit import AuditMxSeasonUseCase


class Repo:
    def coverage_by_competition_season(self, **kwargs):
        return {"targets_total": 0, "pending": 0, "in_progress": 0, "parsed": 0, "retry_scheduled": 0, "blocked": 0, "failed_permanent": 0, "matches_total": 0, "raw_pages_total": 0, "duplicates_detected": 0, "coverage_estimated": 0.0}


class Session:
    def execute(self, *args, **kwargs):
        class R:
            def mappings(self):
                return []
        return R()


class UoW:
    scrape_targets = Repo()
    session = Session()


def test_audit_zero_targets() -> None:
    out = AuditMxSeasonUseCase(uow=UoW()).execute(competition="clausura_mexico", year=2026)
    assert out["targets_total"] == 0
    assert out["matches_total"] == 0
