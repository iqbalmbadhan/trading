"""Phase 3: token-bucket rate limiter tests."""

import asyncio
import time

import pytest

from app.exchanges.rate_limiter import TokenBucketRateLimiter


def test_invalid_params():
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(rate=0, capacity=1)
    with pytest.raises(ValueError):
        TokenBucketRateLimiter(rate=1, capacity=0)


async def test_burst_then_throttle():
    limiter = TokenBucketRateLimiter(rate=10, capacity=2)
    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    burst_elapsed = time.monotonic() - start
    assert burst_elapsed < 0.05  # two tokens available immediately

    await limiter.acquire()  # must wait ~0.1s for one token to refill
    throttled_elapsed = time.monotonic() - start
    assert throttled_elapsed >= 0.09


async def test_requesting_more_than_capacity_raises():
    limiter = TokenBucketRateLimiter(rate=1, capacity=1)
    with pytest.raises(ValueError):
        await limiter.acquire(tokens=2)


async def test_concurrent_acquire_serialized():
    limiter = TokenBucketRateLimiter(rate=20, capacity=1)
    start = time.monotonic()
    await asyncio.gather(*(limiter.acquire() for _ in range(3)))
    elapsed = time.monotonic() - start
    # 1 immediate + 2 refilled at 20/s -> ~0.1s minimum.
    assert elapsed >= 0.09
