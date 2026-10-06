"""Reusable timeout policy for remote and background operations."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import TypeVar

T = TypeVar("T")


class OperationTimeoutError(TimeoutError):
    """Raised when a named operation exceeds its configured deadline."""


async def with_timeout(
    awaitable: Awaitable[T], seconds: float, operation: str = "operation"
) -> T:
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    try:
        return await asyncio.wait_for(awaitable, seconds)
    except asyncio.TimeoutError as exc:
        raise OperationTimeoutError(f"{operation} exceeded {seconds}s") from exc
