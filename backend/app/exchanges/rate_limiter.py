"""Async token-bucket rate limiter, one bucket per exchange instance."""

import asyncio
import time


class TokenBucketRateLimiter:
    """Refills `rate` tokens per second up to `capacity`.

    `acquire()` blocks until a token is available so callers naturally
    pace themselves against exchange-published limits.
    """

    def __init__(self, rate: float, capacity: int) -> None:
        if rate <= 0 or capacity <= 0:
            raise ValueError("rate and capacity must be positive")
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._updated
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        self._updated = now

    async def acquire(self, tokens: int = 1) -> None:
        if tokens > self.capacity:
            raise ValueError("requested tokens exceed bucket capacity")
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                deficit = tokens - self._tokens
                wait_for = deficit / self.rate
            await asyncio.sleep(wait_for)
