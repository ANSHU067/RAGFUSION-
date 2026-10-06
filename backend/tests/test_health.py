"""Health probes reuse Redis and remain bounded and cancellable."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ConnectionError, TimeoutError as RedisTimeoutError

from app.services.health import check_redis_connection


@pytest.mark.parametrize("error", [ConnectionError(), RedisTimeoutError(), OSError()])
async def test_redis_failure_reports_unhealthy_without_closing_pool(error):
    redis = AsyncMock()
    redis.ping.side_effect = error

    assert await check_redis_connection(redis) is False
    redis.aclose.assert_not_called()


async def test_missing_shared_redis_reports_unhealthy():
    assert await check_redis_connection(None) is False


async def test_redis_ping_deadline_keeps_event_loop_responsive():
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def stalled_ping():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    redis = AsyncMock()
    redis.ping.side_effect = stalled_ping
    probe = asyncio.create_task(check_redis_connection(redis))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        # Other work must run while the Redis probe is pending.
        await asyncio.sleep(0)
        assert not probe.done()
        # The production 2-second deadline must cancel the stalled ping.
        assert await asyncio.wait_for(probe, timeout=3) is False
        assert cancelled.is_set()
        redis.aclose.assert_not_called()
    finally:
        probe.cancel()
        await asyncio.gather(probe, return_exceptions=True)


async def test_redis_probe_propagates_request_cancellation():
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def stalled_ping():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    redis = AsyncMock()
    redis.ping.side_effect = stalled_ping
    probe = asyncio.create_task(check_redis_connection(redis))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        probe.cancel()
        with pytest.raises(asyncio.CancelledError):
            await probe
        assert cancelled.is_set()
        redis.aclose.assert_not_called()
    finally:
        probe.cancel()
        await asyncio.gather(probe, return_exceptions=True)
