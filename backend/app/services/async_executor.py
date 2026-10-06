"""Bounded asynchronous execution and supervised background work."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


class AsyncExecutor:
    """Limits concurrency and tracks tasks so cancellation never leaks work."""

    def __init__(self, max_concurrency: int = 16, queue_size: int = 1_000) -> None:
        if max_concurrency <= 0 or queue_size <= 0:
            raise ValueError("max_concurrency and queue_size must be positive")
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._queue_size = queue_size
        self._tasks: set[asyncio.Task[object]] = set()

    async def run(
        self, operation: Callable[[], Awaitable[T]], timeout: float | None = None
    ) -> T:
        async with self._semaphore:
            coroutine = operation()
            return (
                await asyncio.wait_for(coroutine, timeout)
                if timeout
                else await coroutine
            )

    async def map(
        self,
        operations: Iterable[Callable[[], Awaitable[T]]],
        timeout: float | None = None,
    ) -> list[T]:
        async def execute(operation: Callable[[], Awaitable[T]]) -> T:
            return await self.run(operation, timeout)

        async with asyncio.TaskGroup() as group:
            tasks = [group.create_task(execute(operation)) for operation in operations]
        return [task.result() for task in tasks]

    def submit(
        self, operation: Callable[[], Awaitable[object]], timeout: float | None = None
    ) -> asyncio.Task[object]:
        if len(self._tasks) >= self._queue_size:
            raise asyncio.QueueFull("background task queue is full")
        task = asyncio.create_task(self.run(operation, timeout))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def shutdown(self) -> None:
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
