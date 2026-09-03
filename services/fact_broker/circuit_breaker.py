"""
services/fact_broker/circuit_breaker.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In-memory circuit breaker for external source calls.
"""

import logging
import time
from typing import Any, Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

class CircuitOpenError(Exception):
    """Raised when the circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Per-source circuit breaker.
    """
    def __init__(self, name: str, max_failures: int = 3, cooldown_seconds: int = 120):
        self.name = name
        self.max_failures = max_failures
        self.cooldown_seconds = cooldown_seconds

        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def _update_state(self) -> None:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.cooldown_seconds:
                self.state = "HALF_OPEN"
                logger.info("CircuitBreaker '%s' transitioning to HALF_OPEN", self.name)

    async def call(self, fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any) -> T:
        self._update_state()

        if self.state == "OPEN":
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN. Try again later.")

        try:
            result = await fn(*args, **kwargs)
            # Success: reset
            if self.state != "CLOSED":
                logger.info("CircuitBreaker '%s' transitioning to CLOSED", self.name)
            self.failures = 0
            self.state = "CLOSED"
            return result
        except Exception as exc:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.max_failures:
                self.state = "OPEN"
                logger.warning("CircuitBreaker '%s' transitioning to OPEN after %d failures", self.name, self.failures)
            raise exc
