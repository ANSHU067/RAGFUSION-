from __future__ import annotations

import asyncio

import pytest

from app.core.cache import TTLCache
from app.core.cache_manager import CacheManager, stable_cache_key


@pytest.mark.asyncio
async def test_ttl_cache_tracks_hits_misses_and_evictions() -> None:
    cache: TTLCache[str, int] = TTLCache(max_size=2, default_ttl=60)
    assert await cache.get("missing") is None
    await cache.set("one", 1)
    assert await cache.get("one") == 1
    await cache.set("two", 2)
    await cache.set("three", 3)
    assert await cache.get("one") is None
    stats = await cache.stats()
    assert stats.hits == 1 and stats.misses == 2 and stats.evictions == 1
    assert stats.memory_bytes > 0


@pytest.mark.asyncio
async def test_cache_expiry_invalidation_warming_and_namespaces() -> None:
    manager = CacheManager(max_size=10)
    key = stable_cache_key("question", "What is RAG?", {"top_k": 5})
    await manager.warm("retrieval", [(key, ["result"])])
    assert await manager.retrieval_cache.get(key) == ["result"]
    assert await manager.invalidate("retrieval", key)
    await manager.response_cache.set("temporary", "value", ttl=0.01)
    await asyncio.sleep(0.02)
    assert (await manager.cleanup())["response"] == 1
