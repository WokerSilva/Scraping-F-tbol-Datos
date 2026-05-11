from besoccer_scraper.application.scraping import ScrapeMatchesUseCase
from besoccer_scraper.domain.enums import TargetStatus


class Repo:
    def mark_transition(self, **kwargs):
        return True

class U:
    scrape_targets = Repo()


def test_mark_target_blocked_does_not_crash():
    uc = ScrapeMatchesUseCase(uow=U(), http_client=None, parser=None, request_policy=None)
    assert uc._mark_target(1, TargetStatus.BLOCKED, error="403") is True
