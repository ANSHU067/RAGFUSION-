"""Named cache registry for embeddings, retrievals, responses, queries and sessions."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, TypeVar

from app.core.cache import CacheStats, TTLCache

ValueT = TypeVar("ValueT")


def stable_cache_key(namespace: str, *parts: object) -> str:
    """Create deterministic keys without retaining large request payloads as keys."""
    payload = json.dumps(parts, sort_keys=True, default=str, separators=(",", ":"))
    return f"{namespace}:{hashlib.sha256(payload.encode()).hexdigest()}"


class CacheManager:
    """Dependency-injectable collection of bounded cache namespaces."""

    def __init__(self, max_size: int = 1_024) -> None:
        self.embedding_cache: TTLCache[str, Any] = TTLCache(max_size, 86_400)
        self.retrieval_cache: TTLCache[str, Any] = TTLCache(max_size, 300)
        self.response_cache: TTLCache[str, Any] = TTLCache(max_size, 120)
        self.query_cache: TTLCache[str, Any] = TTLCache(max_size, 60)
        self.session_cache: TTLCache[str, Any] = TTLCache(max_size, 300)
        self._caches = {
            "embedding": self.embedding_cache,
            "retrieval": self.retrieval_cache,
            "response": self.response_cache,
            "query": self.query_cache,
            "session": self.session_cache,
        }

    def cache(self, name: str) -> TTLCache[str, Any]:
        try:
            return self._caches[name]
        except KeyError as exc:
            raise ValueError(f"Unknown cache namespace: {name}") from exc

    async def get_or_set(
        self,
        name: str,
        key: str,
        factory: Callable[[], Awaitable[ValueT]],
        ttl: float | None = None,
    ) -> ValueT:
        return await self.cache(name).get_or_set(key, factory, ttl)

    async def invalidate(self, name: str, key: str) -> bool:
        return await self.cache(name).invalidate(key)

    async def invalidate_prefix(self, name: str, prefix: str) -> int:
        return await self.cache(name).invalidate_prefix(prefix)

    async def warm(
        self, name: str, values: Iterable[tuple[str, Any]], ttl: float | None = None
    ) -> None:
        await self.cache(name).warm(values, ttl)

    async def cleanup(self) -> dict[str, int]:
        return {name: await cache.cleanup() for name, cache in self._caches.items()}

    async def stats(self) -> dict[str, CacheStats]:
        return {name: await cache.stats() for name, cache in self._caches.items()}


cache_manager = CacheManager()
