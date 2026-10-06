"""Async sliding-window rate limiter with burst protection."""

from __future__ import annotations

import asyncio
import hashlib
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError
from app.config.branding_compat import RATE_LIMIT_NAMESPACE


@dataclass(frozen=True, slots=True)
class RateLimitPolicy:
    limit: int
    window_seconds: float
    burst: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1 or self.window_seconds <= 0 or self.burst < 0:
            raise ValueError("rate limit values must be positive")


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


class InMemoryRateLimiter:
    """Explicit test injection; never a production outage fallback."""

    def __init__(self, clock=monotonic) -> None:
        self._clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str, policy: RateLimitPolicy) -> RateLimitResult:
        now = self._clock()
        async with self._lock:
            bucket = self._requests[key]
            cutoff = now - policy.window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            capacity = policy.limit + policy.burst
            if len(bucket) >= capacity:
                return RateLimitResult(
                    False,
                    0,
                    max(1, int(bucket[0] + policy.window_seconds - now + 0.999)),
                )
            bucket.append(now)
            return RateLimitResult(True, max(0, capacity - len(bucket)), 0)

    async def reset(self, key: str) -> None:
        async with self._lock:
            self._requests.pop(key, None)

    async def aclose(self) -> None:
        self._requests.clear()


class RateLimitUnavailable(Exception):
    """The distributed quota cannot be verified."""


class RateLimiter(Protocol):
    async def check(self, key: str, policy: RateLimitPolicy) -> RateLimitResult: ...
    async def aclose(self) -> None: ...


class RedisRateLimiter:
    """Exact sliding window, with Redis time and one atomic script per request."""

    SCRIPT = """
local clock = redis.call('TIME')
local now = tonumber(clock[1]) * 1000 + math.floor(tonumber(clock[2]) / 1000)
local window = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now - window)
local used = redis.call('ZCARD', KEYS[1])
if used >= capacity then
    local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
    return {0, 0, math.max(1, tonumber(oldest[2]) + window - now)}
end
local sequence = redis.call('INCR', KEYS[2])
redis.call('PEXPIRE', KEYS[2], window)
redis.call('ZADD', KEYS[1], now, tostring(sequence))
redis.call('PEXPIRE', KEYS[1], window)
return {1, capacity - used - 1, 0}
"""

    def __init__(self, url: str, *, prefix: str = RATE_LIMIT_NAMESPACE, timeout: float = 1.0) -> None:
        self.prefix = prefix
        self.timeout = timeout
        self.redis = Redis.from_url(
            url, socket_connect_timeout=timeout, socket_timeout=timeout,
            retry_on_timeout=False, max_connections=100,
        )

    async def check(self, key: str, policy: RateLimitPolicy) -> RateLimitResult:
        digest = hashlib.sha256(key.encode()).hexdigest()
        # Both keys share a Redis Cluster hash slot.
        bucket = f"{self.prefix}:{{{digest}}}"
        try:
            async with asyncio.timeout(self.timeout):
                allowed, remaining, retry_ms = await self.redis.eval(
                    self.SCRIPT, 2, bucket + ":events", bucket + ":sequence",
                    max(1, math.ceil(policy.window_seconds * 1000)), policy.limit + policy.burst,
                )
        except (RedisError, TimeoutError, OSError) as exc:
            raise RateLimitUnavailable("Rate limit service unavailable") from exc
        return RateLimitResult(bool(allowed), int(remaining), math.ceil(int(retry_ms) / 1000))

    async def aclose(self) -> None:
        await self.redis.aclose()
