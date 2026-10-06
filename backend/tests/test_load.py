from __future__ import annotations

import asyncio

import pytest

from app.services.async_executor import AsyncExecutor


@pytest.mark.asyncio
async def test_executor_handles_100_concurrent_requests() -> None:
    executor = AsyncExecutor(max_concurrency=10)
    active = 0
    peak = 0

    async def work() -> int:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return 1

    assert sum(await executor.map([work for _ in range(100)])) == 100
    assert peak <= 10
