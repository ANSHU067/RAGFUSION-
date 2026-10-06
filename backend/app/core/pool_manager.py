"""Managed HTTP, worker and lazy instance pools."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PoolStats:
    capacity: int
    in_use: int
    available: int


class ResourcePool(Generic[T]):
    """Semaphore-bounded pool that creates instances lazily and safely."""

    def __init__(self, factory: Callable[[], Awaitable[T]], max_size: int = 8) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        self._factory, self._max_size = factory, max_size
        self._available: asyncio.LifoQueue[T] = asyncio.LifoQueue(max_size)
        self._created = 0
        self._in_use = 0
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, timeout: float | None = None) -> AsyncIterator[T]:
        async def take() -> T:
            try:
                item = self._available.get_nowait()
            except asyncio.QueueEmpty:
                async with self._lock:
                    if self._created < self._max_size:
                        self._created += 1
                        try:
                            return await self._factory()
                        except Exception:
                            self._created -= 1
                            raise
                item = await self._available.get()
            return item

        item = await asyncio.wait_for(take(), timeout) if timeout else await take()
        self._in_use += 1
        try:
            yield item
        finally:
            self._in_use -= 1
            await self._available.put(item)

    async def resize(self, max_size: int) -> None:
        if max_size <= 0 or max_size < self._in_use:
            raise ValueError(
                "max_size must be positive and not less than in-use resources"
            )
        async with self._lock:
            self._max_size = max_size

    async def stats(self) -> PoolStats:
        return PoolStats(self._max_size, self._in_use, self._available.qsize())


class LazyResource(Generic[T]):
    """Loads an expensive dependency on first use and can unload it after idle time."""

    def __init__(
        self,
        factory: Callable[[], Awaitable[T]],
        closer: Callable[[T], Awaitable[None]] | None = None,
    ) -> None:
        self._factory, self._closer = factory, closer
        self._instance: T | None = None
        self._last_used = time.monotonic()
        self._lock = asyncio.Lock()

    async def get(self) -> T:
        async with self._lock:
            if self._instance is None:
                self._instance = await self._factory()
            self._last_used = time.monotonic()
            return self._instance

    async def unload_if_idle(self, idle_seconds: float) -> bool:
        async with self._lock:
            if (
                self._instance is None
                or time.monotonic() - self._last_used < idle_seconds
            ):
                return False
            instance, self._instance = self._instance, None
            if self._closer:
                await self._closer(instance)
            return True
