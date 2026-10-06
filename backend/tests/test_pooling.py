from __future__ import annotations

import asyncio

import pytest

from app.core.pool_manager import LazyResource, ResourcePool


@pytest.mark.asyncio
async def test_resource_pool_reuses_and_reports_capacity() -> None:
    created = 0

    async def factory() -> object:
        nonlocal created
        created += 1
        return object()

    pool = ResourcePool(factory, max_size=1)
    async with pool.acquire() as first:
        assert (await pool.stats()).in_use == 1
    async with pool.acquire() as second:
        assert first is second
    assert created == 1


@pytest.mark.asyncio
async def test_lazy_resource_loads_once_and_unloads_when_idle() -> None:
    resource = LazyResource(lambda: asyncio.sleep(0, result="model"))
    assert await resource.get() == "model"
    assert await resource.unload_if_idle(0)
