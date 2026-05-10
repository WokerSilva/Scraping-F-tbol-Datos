from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int


@dataclass(frozen=True)
class RequestPolicy:
    timeout_seconds: float
    user_agent: str
