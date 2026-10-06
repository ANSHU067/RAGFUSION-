"""Bounded, thread-safe in-process caches used by performance services."""

from __future__ import annotations

import asyncio
import sys
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

KeyT = TypeVar("KeyT")
ValueT = TypeVar("ValueT")


@dataclass(frozen=True, slots=True)
class CacheStats:
    """A point-in-time view of a cache's behavior and approximate memory use."""

    hits: int
    misses: int
    evictions: int
    size: int
    memory_bytes: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    @property
    def miss_rate(self) -> float:
        total = self.hits + self.misses
        return self.misses / total if total else 0.0


@dataclass(slots=True)
class _Entry(Generic[ValueT]):
    value: ValueT
    expires_at: float | None


class TTLCache(Generic[KeyT, ValueT]):
    """An async-safe LRU cache with optional per-entry TTLs.

    Values are deliberately kept in-process; callers must not cache user-specific
    data without including the user/tenant identifier in the key.
    """

    def __init__(
        self, max_size: int = 1_024, default_ttl: float | None = 300.0
    ) -> None:
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if default_ttl is not None and default_ttl <= 0:
            raise ValueError("default_ttl must be positive or None")
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._items: OrderedDict[KeyT, _Entry[ValueT]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._inflight: dict[KeyT, asyncio.Task[ValueT]] = {}
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    @staticmethod
    def _expired(entry: _Entry[ValueT], now: float) -> bool:
        return entry.expires_at is not None and entry.expires_at <= now

    async def get(self, key: KeyT) -> ValueT | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None or self._expired(entry, time.monotonic()):
                if entry is not None:
                    del self._items[key]
                self._misses += 1
                return None
            self._items.move_to_end(key)
            self._hits += 1
            return entry.value

    async def set(self, key: KeyT, value: ValueT, ttl: float | None = None) -> None:
        effective_ttl = self.default_ttl if ttl is None else ttl
        if effective_ttl is not None and effective_ttl <= 0:
            raise ValueError("ttl must be positive or None")
        expires_at = None if effective_ttl is None else time.monotonic() + effective_ttl
        async with self._lock:
            self._items[key] = _Entry(value=value, expires_at=expires_at)
            self._items.move_to_end(key)
            while len(self._items) > self.max_size:
                self._items.popitem(last=False)
                self._evictions += 1

    async def get_or_set(
        self,
        key: KeyT,
        factory: Callable[[], Awaitable[ValueT]],
        ttl: float | None = None,
    ) -> ValueT:
        """Return a cached value or compute it once for concurrent callers."""
        value = await self.get(key)
        if value is not None:
            return value

        async with self._lock:
            task = self._inflight.get(key)
            if task is None:

                async def populate() -> ValueT:
                    value = await factory()
                    await self.set(key, value, ttl)
                    return value

                task = asyncio.create_task(populate())
                self._inflight[key] = task
                task.add_done_callback(lambda _: self._inflight.pop(key, None))
        # Shield shared work: one cancelled HTTP request must not abort peers.
        return await asyncio.shield(task)

    async def invalidate(self, key: KeyT) -> bool:
        async with self._lock:
            return self._items.pop(key, None) is not None

    async def invalidate_prefix(self, prefix: str) -> int:
        async with self._lock:
            keys = [key for key in self._items if str(key).startswith(prefix)]
            for key in keys:
                del self._items[key]
            return len(keys)

    async def cleanup(self) -> int:
        """Remove expired entries and return their count."""
        now = time.monotonic()
        async with self._lock:
            keys = [
                key for key, entry in self._items.items() if self._expired(entry, now)
            ]
            for key in keys:
                del self._items[key]
            return len(keys)

    async def clear(self) -> None:
        async with self._lock:
            self._items.clear()

    async def warm(
        self, values: Iterable[tuple[KeyT, ValueT]], ttl: float | None = None
    ) -> None:
        for key, value in values:
            await self.set(key, value, ttl)

    async def stats(self) -> CacheStats:
        async with self._lock:
            memory = sum(
                sys.getsizeof(key) + sys.getsizeof(entry.value)
                for key, entry in self._items.items()
            )
            return CacheStats(
                self._hits, self._misses, self._evictions, len(self._items), memory
            )


LRUCache = TTLCache
