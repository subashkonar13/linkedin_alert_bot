"""
Retry Engine — Wraps alert creation with exponential backoff and max-attempts logic.
"""

import time
from typing import Callable, Any
from src.logger import get_logger

logger = get_logger(__name__)


class RetryEngine:
    """
    Generic retry wrapper with exponential backoff.

    Args:
        max_attempts: Total number of tries including the first.
        base_delay:   Seconds to wait after first failure.
        backoff:      Multiplier applied after each failure.
        max_delay:    Upper cap for any single wait period.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 5.0,
        backoff: float = 2.0,
        max_delay: float = 60.0
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.backoff = backoff
        self.max_delay = max_delay

    def run(self, func: Callable, *args, **kwargs) -> tuple[Any, bool]:
        """
        Executes func(*args, **kwargs) up to max_attempts times.

        Returns:
            (result, success) — result is the last return value; success is bool.
        """
        delay = self.base_delay
        last_result = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if result and getattr(result, "status", None) == "success":
                    return result, True
                last_result = result
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_attempts} raised exception: {e}")
                last_result = None

            if attempt < self.max_attempts:
                wait = min(delay, self.max_delay)
                logger.info(f"  Retrying in {wait:.0f}s (attempt {attempt}/{self.max_attempts})...")
                time.sleep(wait)
                delay *= self.backoff

        logger.error(f"All {self.max_attempts} attempts exhausted.")
        return last_result, False
