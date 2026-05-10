from besoccer_scraper.application.audit import AuditMxSeasonUseCase


class Repo:
    def coverage_by_competition_season(self, **kwargs):
        assert kwargs["competition"] == "clausura_mexico"
        assert kwargs["season_key"] == "clausura-2026"
        return {"targets_total": 1, "pending": 1, "in_progress": 0, "parsed": 0, "retry_scheduled": 0, "blocked": 0, "failed_permanent": 0, "matches_total": 0, "duplicates_detected": 0}


class Session:
    def execute(self, *args, **kwargs):
        class R:
            def mappings(self):
                return [{"round_label": "JORNADA1", "total": 1}]
        return R()


class UoW:
    scrape_targets = Repo()
    session = Session()


def test_audit_reads_official_columns():
    out = AuditMxSeasonUseCase(uow=UoW()).execute(competition="clausura_mexico", year=2026)
    assert out["targets_total"] == 1
