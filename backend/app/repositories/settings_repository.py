"""Repository for user settings operations."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import UserSettings
from app.repositories.base import Repository

logger = logging.getLogger(__name__)


class SettingsRepository(Repository[UserSettings]):
    """Repository for user settings with specialized operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserSettings)

    async def get_by_user_id(self, user_id: UUID, *, for_update: bool = False) -> UserSettings | None:
        """Get settings for a specific user.

        Args:
            user_id: User ID to fetch settings for

        Returns:
            UserSettings instance or None if not found
        """
        statement = select(UserSettings).where(UserSettings.user_id == user_id)
        if for_update:
            await self.session.flush()
            statement = statement.with_for_update().execution_options(populate_existing=True)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_default(self, user_id: UUID) -> UserSettings:
        """Create default settings for a user.

        Args:
            user_id: User ID to create settings for

        Returns:
            Created UserSettings instance

        Raises:
            IntegrityError: If settings already exist for the user
        """
        # A duplicate insert must not roll back unrelated work in the caller's
        # transaction. The strict create API retains its duplicate-error contract.
        async with self.session.begin_nested():
            settings = UserSettings(user_id=user_id)
            self.session.add(settings)
            await self.session.flush()
        return settings

    async def get_or_create(self, user_id: UUID) -> UserSettings:
        """Get existing settings or create defaults for a user.

        Args:
            user_id: User ID to get or create settings for

        Returns:
            UserSettings instance
        """
        dialect = self.session.get_bind().dialect.name
        if dialect == "postgresql":
            insert = pg_insert
        elif dialect == "sqlite":
            insert = sqlite_insert
        else:
            raise NotImplementedError("Settings require PostgreSQL or SQLite")
        await self.session.execute(
            insert(UserSettings).values(user_id=user_id).on_conflict_do_nothing(
                index_elements=[UserSettings.user_id]
            )
        )
        # Held until the enclosing transaction commits/rolls back. Refresh cached
        # ORM state after waiting, so validation sees the latest committed values.
        settings = await self.get_by_user_id(user_id, for_update=True)
        if settings is None:
            raise RuntimeError("Settings disappeared during initialization")
        return settings

    async def update_settings(
        self, user_id: UUID, updates: dict[str, Any]
    ) -> UserSettings | None:
        """Update user settings with partial updates.

        Args:
            user_id: User ID to update settings for
            updates: Dictionary of field names and new values

        Returns:
            Updated UserSettings instance or None if not found
        """
        settings = await self.get_by_user_id(user_id, for_update=True)
        if settings is None:
            return None

        for field, value in updates.items():
            if hasattr(settings, field):
                setattr(settings, field, value)

        await self.session.flush()
        return settings

    async def reset_to_defaults(self, user_id: UUID) -> UserSettings | None:
        """Reset user settings to default values.

        Args:
            user_id: User ID to reset settings for

        Returns:
            Reset UserSettings instance or None if not found
        """
        from app.models.settings import LLMProvider, EmbeddingProvider
        from app.schemas.settings import DEFAULT_SETTINGS

        settings = await self.get_by_user_id(user_id, for_update=True)
        if settings is None:
            return None

        # Reset all fields to defaults explicitly
        settings.provider = LLMProvider(DEFAULT_SETTINGS["provider"])
        settings.model_name = DEFAULT_SETTINGS["model_name"]
        settings.embedding_provider = EmbeddingProvider(
            DEFAULT_SETTINGS["embedding_provider"]
        )
        settings.embedding_model = DEFAULT_SETTINGS["embedding_model"]
        settings.temperature = DEFAULT_SETTINGS["temperature"]
        settings.top_k = DEFAULT_SETTINGS["top_k"]
        settings.max_tokens = DEFAULT_SETTINGS["max_tokens"]
        settings.chunk_size = DEFAULT_SETTINGS["chunk_size"]
        settings.chunk_overlap = DEFAULT_SETTINGS["chunk_overlap"]
        settings.similarity_threshold = DEFAULT_SETTINGS["similarity_threshold"]
        settings.reranking_enabled = DEFAULT_SETTINGS["reranking_enabled"]

        await self.session.flush()
        return settings

    async def delete_by_user_id(self, user_id: UUID) -> bool:
        """Delete user settings.

        Args:
            user_id: User ID to delete settings for

        Returns:
            True if deleted, False if not found
        """
        settings = await self.get_by_user_id(user_id, for_update=True)
        if settings is None:
            return False

        await self.session.delete(settings)
        await self.session.flush()
        return True
