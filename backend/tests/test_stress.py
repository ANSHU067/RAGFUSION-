from __future__ import annotations

import asyncio

import pytest

from app.services.async_executor import AsyncExecutor


@pytest.mark.asyncio
async def test_executor_recovers_from_a_burst_of_1000_requests() -> None:
    executor = AsyncExecutor(max_concurrency=50, queue_size=1_100)

    async def request() -> int:
        await asyncio.sleep(0)
        return 1

    results = await executor.map([request for _ in range(1_000)])
    assert len(results) == 1_000 and sum(results) == 1_000
