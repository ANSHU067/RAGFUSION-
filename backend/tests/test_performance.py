from __future__ import annotations

import pytest

from app.core.performance import PerformanceMonitor
from app.utils.timeouts import OperationTimeoutError, with_timeout


@pytest.mark.asyncio
async def test_monitor_reports_rolling_latency() -> None:
    monitor = PerformanceMonitor()
    await monitor.record(10, 200)
    await monitor.record(30, 500)
    snapshot = await monitor.snapshot()
    assert snapshot.requests == 2 and snapshot.errors == 1
    assert snapshot.average_latency_ms == 20 and snapshot.p95_latency_ms == 30


@pytest.mark.asyncio
async def test_timeout_converts_asyncio_timeout() -> None:
    with pytest.raises(OperationTimeoutError):
        await with_timeout(__import__("asyncio").sleep(0.1), 0.001, "test")
