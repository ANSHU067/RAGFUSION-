"""Performance middleware and light-weight runtime instrumentation."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    requests: int
    errors: int
    average_latency_ms: float
    p95_latency_ms: float


class PerformanceMonitor:
    """Bounded rolling latency monitor with no request-body retention."""

    def __init__(self, window_size: int = 2_000) -> None:
        self._latencies: deque[float] = deque(maxlen=window_size)
        self._requests = 0
        self._errors = 0
        self._lock = asyncio.Lock()

    async def record(self, elapsed_ms: float, status_code: int) -> None:
        async with self._lock:
            self._requests += 1
            self._errors += int(status_code >= 500)
            self._latencies.append(elapsed_ms)

    async def snapshot(self) -> PerformanceSnapshot:
        async with self._lock:
            samples = sorted(self._latencies)
            p95 = (
                samples[min(len(samples) - 1, int(len(samples) * 0.95))]
                if samples
                else 0.0
            )
            average = sum(samples) / len(samples) if samples else 0.0
            return PerformanceSnapshot(self._requests, self._errors, average, p95)


performance_monitor = PerformanceMonitor()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Adds an inexpensive duration header and records response latency."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1_000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"
        await performance_monitor.record(elapsed_ms, response.status_code)
        return response
