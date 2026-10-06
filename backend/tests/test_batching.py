from __future__ import annotations

import pytest

from app.services.batch_service import BatchService, chunked


def test_chunked_enforces_batch_size() -> None:
    assert [list(part) for part in chunked([1, 2, 3, 4, 5], 2)] == [[1, 2], [3, 4], [5]]
    with pytest.raises(ValueError):
        list(chunked([1], 0))


@pytest.mark.asyncio
async def test_batch_service_preserves_order() -> None:
    service = BatchService(batch_size=3, max_concurrency=2)

    async def processor(batch: list[int]) -> list[int]:
        return [item * 2 for item in batch]

    assert await service.process(list(range(10)), processor) == [
        item * 2 for item in range(10)
    ]
