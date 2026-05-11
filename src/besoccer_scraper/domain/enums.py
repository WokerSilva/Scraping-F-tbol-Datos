from enum import Enum


class TargetStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PARSED = "parsed"
    RETRY_SCHEDULED = "retry_scheduled"
    BLOCKED = "blocked"
    FAILED_PERMANENT = "failed_permanent"
    FAILED = "failed"


class TargetType(str, Enum):
    MATCH = "match"
    TEAM_MATCHES = "team_matches"
    COMPETITION = "competition"


class RunMode(str, Enum):
    DISCOVER = "discover"
    SCRAPE = "scrape"
    AUDIT = "audit"
    PIPELINE = "pipeline"


class PipelineMode(str, Enum):
    MATCH = "match"
    PENDING_MATCHES = "pending_matches"
