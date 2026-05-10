from enum import Enum


class RunMode(str, Enum):
    DISCOVER = "discover"
    SCRAPE = "scrape"
    AUDIT = "audit"
    PIPELINE = "pipeline"
