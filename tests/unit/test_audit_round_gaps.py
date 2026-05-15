from besoccer_scraper.application.audit import AuditMxSeasonUseCase


class Repo:
    def coverage_by_competition_season(self, **kwargs):
        return {"targets_total": 144, "pending": 0, "in_progress": 0, "parsed": 144, "retry_scheduled": 0, "blocked": 0, "failed_permanent": 0, "matches_total": 144, "duplicates_detected": 0}


class Session:
    def execute(self, *args, **kwargs):
        class R:
            def mappings(self):
                return [
                    {"round_label": "JORNADA1", "total": 9},
                    {"round_label": "JORNADA2", "total": 9},
                    {"round_label": "JORNADA3", "total": 18},
                ]
        return R()


class Uow:
    scrape_targets = Repo()
    session = Session()


def test_audit_detects_missing_and_duplicate_round_counts():
    out = AuditMxSeasonUseCase(uow=Uow()).execute(competition="clausura_mexico", year=2026)
    assert "JORNADA6" in out["missing_rounds"]
    assert out["duplicate_count_rounds"]["JORNADA3"] == 18
    assert out["irregular_round_counts"]["JORNADA3"] == 18
