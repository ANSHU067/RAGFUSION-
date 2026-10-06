"""Small reusable async repository with explicit unit-of-work ownership."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from collections.abc import Sequence

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class Repository(Generic[ModelT]):
    """CRUD operations that flush but never commit the caller's transaction."""

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get(self, identifier: Any) -> ModelT | None:
        return await self.session.get(self.model, identifier)

    async def list(self, *, offset: int = 0, limit: int = 100) -> list[ModelT]:
        if offset < 0 or not 1 <= limit <= 1_000:
            raise ValueError("offset must be non-negative and limit must be 1..1000")
        result = await self.session.scalars(
            select(self.model).offset(offset).limit(limit)
        )
        return [instance for instance in result]

    async def create_many(self, values: Sequence[dict[str, Any]]) -> list[ModelT]:
        """Insert a bounded collection with one flush instead of N round trips."""
        instances = [self.model(**item) for item in values]
        self.session.add_all(instances)
        await self.session.flush()
        return instances

    async def update_many(self, identifiers: Sequence[Any], **values: Any) -> int:
        """Bulk-update rows by primary key without loading every model instance."""
        if not identifiers or not values:
            return 0
        primary_key = self.model.__mapper__.primary_key[0]
        result = await self.session.execute(
            update(self.model).where(primary_key.in_(identifiers)).values(**values)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def create(self, **values: Any) -> ModelT:
        instance = self.model(**values)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelT, **values: Any) -> ModelT:
        for field, value in values.items():
            setattr(instance, field, value)
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelT) -> None:
        await self.session.delete(instance)
        await self.session.flush()
