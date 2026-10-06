"""Memory-bounded batch processing primitives."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")


def chunked(items: Sequence[T], batch_size: int) -> Iterable[Sequence[T]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    for offset in range(0, len(items), batch_size):
        yield items[offset : offset + batch_size]


class BatchService:
    """Processes batches with bounded parallelism and retry-compatible callbacks."""

    def __init__(self, batch_size: int = 32, max_concurrency: int = 4) -> None:
        self.batch_size = batch_size
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def process(
        self,
        items: Sequence[T],
        processor: Callable[[Sequence[T]], Awaitable[Sequence[R]]],
    ) -> list[R]:
        async def process_one(batch: Sequence[T]) -> Sequence[R]:
            async with self._semaphore:
                return await processor(batch)

        batches = list(chunked(items, self.batch_size))
        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(process_one(batch)) for batch in batches]
        return [result for task in tasks for result in task.result()]
