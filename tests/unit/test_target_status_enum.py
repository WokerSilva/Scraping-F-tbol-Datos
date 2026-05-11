from besoccer_scraper.domain.enums import TargetStatus


def test_target_status_blocked_exists():
    assert TargetStatus.BLOCKED.value == "blocked"


def test_target_status_retry_and_failed_permanent_exist():
    assert TargetStatus.RETRY_SCHEDULED.value == "retry_scheduled"
    assert TargetStatus.FAILED_PERMANENT.value == "failed_permanent"
