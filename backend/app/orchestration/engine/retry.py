"""Retry policy for transient agent / stage failures."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0

    def should_retry(self, attempt: int, retryable: bool) -> bool:
        return retryable and attempt < self.max_retries

    def delay_seconds(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (2 ** max(attempt - 1, 0))
        return min(delay, self.max_delay_seconds)
