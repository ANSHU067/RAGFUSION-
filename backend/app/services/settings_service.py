"""Settings service for user-specific AI configuration."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import UserSettings
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import (
    DEFAULT_SETTINGS,
    SettingsCreate,
    SettingsResponse,
    SettingsResetResponse,
    SettingsUpdate,
)

logger = logging.getLogger(__name__)


class SettingsValidationError(ValueError):
    """Raised when settings validation fails."""

    pass


class SettingsNotFoundError(LookupError):
    """Raised when settings are not found for a user."""

    pass


class SettingsService:
    """Service layer for managing user settings."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SettingsRepository(session)

    async def get_settings(self, user_id: UUID) -> SettingsResponse:
        """Get settings for a user, creating defaults if not exist.

        Args:
            user_id: User ID to fetch settings for

        Returns:
            SettingsResponse with current settings
        """
        settings = await self.repository.get_or_create(user_id)
        return self._to_response(settings)

    async def update_settings(
        self, user_id: UUID, updates: SettingsUpdate
    ) -> SettingsResponse:
        """Update user settings with validation.

        Args:
            user_id: User ID to update settings for
            updates: SettingsUpdate with fields to update

        Returns:
            SettingsResponse with updated settings

        Raises:
            SettingsValidationError: If validation fails
        """
        from app.models.settings import LLMProvider, EmbeddingProvider

        # Convert to dict, excluding None values
        update_dict = updates.model_dump(exclude_unset=True, exclude_none=True)

        if not update_dict:
            # No updates provided, return current settings
            return await self.get_settings(user_id)

        # Get or create settings first
        settings = await self.repository.get_or_create(user_id)

        # Validate against the resulting state so partial chunking updates
        # cannot leave overlap greater than or equal to chunk size.
        validation_data = {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
        }
        validation_data.update(update_dict)
        self._validate_updates(validation_data)

        # Apply updates with enum conversion
        for field, value in update_dict.items():
            if hasattr(settings, field):
                if field == "provider" and isinstance(value, str):
                    value = LLMProvider(value)
                elif field == "embedding_provider" and isinstance(value, str):
                    value = EmbeddingProvider(value)
                setattr(settings, field, value)

        await self.session.commit()
        logger.info(f"Updated settings for user {user_id}: {list(update_dict.keys())}")
        return self._to_response(settings)

    async def reset_settings(self, user_id: UUID) -> SettingsResetResponse:
        """Reset user settings to default values.

        Args:
            user_id: User ID to reset settings for

        Returns:
            SettingsResetResponse with reset settings

        Raises:
            SettingsNotFoundError: If user settings don't exist
        """
        settings = await self.repository.reset_to_defaults(user_id)
        if settings is None:
            raise SettingsNotFoundError(f"Settings not found for user {user_id}")

        await self.session.commit()
        logger.info(f"Reset settings to defaults for user {user_id}")
        return SettingsResetResponse(
            message="Settings reset to defaults successfully",
            settings=self._to_response(settings),
        )

    async def load_default_settings(self, user_id: UUID) -> SettingsResponse:
        """Load default settings for a user (create if not exist).

        Args:
            user_id: User ID to load defaults for

        Returns:
            SettingsResponse with default settings
        """
        settings = await self.repository.get_or_create(user_id)
        return self._to_response(settings)

    def validate_settings(
        self, data: SettingsCreate | SettingsUpdate
    ) -> dict[str, Any]:
        """Validate settings data without persisting.

        Args:
            data: SettingsCreate or SettingsUpdate to validate

        Returns:
            Validated data as dictionary

        Raises:
            SettingsValidationError: If validation fails
        """
        try:
            # Pydantic validation happens automatically on model creation
            # Additional cross-field validation
            update_dict = data.model_dump(exclude_unset=True, exclude_none=True)
            self._validate_updates(update_dict)
            return update_dict
        except Exception as e:
            if isinstance(e, SettingsValidationError):
                raise
            # Convert pydantic validation errors to SettingsValidationError
            raise SettingsValidationError(str(e))

    def _validate_updates(self, updates: dict[str, Any]) -> None:
        """Perform cross-field validation on updates.

        Args:
            updates: Dictionary of field updates

        Raises:
            SettingsValidationError: If validation fails
        """
        # Validate chunk_overlap < chunk_size if both provided
        chunk_size = updates.get("chunk_size")
        chunk_overlap = updates.get("chunk_overlap")

        if chunk_size is not None and chunk_overlap is not None:
            if chunk_overlap >= chunk_size:
                raise SettingsValidationError(
                    f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})"
                )

        # Validate temperature range
        temperature = updates.get("temperature")
        if temperature is not None and not (0.0 <= temperature <= 2.0):
            raise SettingsValidationError(
                f"temperature must be between 0.0 and 2.0, got {temperature}"
            )

        # Validate top_k range
        top_k = updates.get("top_k")
        if top_k is not None and not (1 <= top_k <= 100):
            raise SettingsValidationError(
                f"top_k must be between 1 and 100, got {top_k}"
            )

        # Validate max_tokens range
        max_tokens = updates.get("max_tokens")
        if max_tokens is not None and not (100 <= max_tokens <= 32000):
            raise SettingsValidationError(
                f"max_tokens must be between 100 and 32000, got {max_tokens}"
            )

        # Validate chunk_size range
        if chunk_size is not None and not (128 <= chunk_size <= 4096):
            raise SettingsValidationError(
                f"chunk_size must be between 128 and 4096, got {chunk_size}"
            )

        # Validate chunk_overlap range
        if chunk_overlap is not None and chunk_overlap < 0:
            raise SettingsValidationError(
                f"chunk_overlap must be >= 0, got {chunk_overlap}"
            )

        # Validate similarity_threshold range
        similarity_threshold = updates.get("similarity_threshold")
        if similarity_threshold is not None and not (
            0.0 <= similarity_threshold <= 1.0
        ):
            raise SettingsValidationError(
                f"similarity_threshold must be between 0.0 and 1.0, got {similarity_threshold}"
            )

    def _to_response(self, settings: UserSettings) -> SettingsResponse:
        """Convert UserSettings model to SettingsResponse schema.

        Args:
            settings: UserSettings model instance

        Returns:
            SettingsResponse schema
        """
        return SettingsResponse(
            id=settings.id,
            user_id=settings.user_id,
            provider=settings.provider.value,
            model_name=settings.model_name,
            embedding_provider=settings.embedding_provider.value,
            embedding_model=settings.embedding_model,
            temperature=settings.temperature,
            top_k=settings.top_k,
            max_tokens=settings.max_tokens,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            similarity_threshold=settings.similarity_threshold,
            reranking_enabled=settings.reranking_enabled,
            created_at=settings.created_at,
            updated_at=settings.updated_at,
        )

    @staticmethod
    def get_default_settings() -> dict[str, Any]:
        """Get default settings dictionary.

        Returns:
            Dictionary of default settings
        """
        return DEFAULT_SETTINGS.copy()


def create_settings_service(session: AsyncSession) -> SettingsService:
    """Factory function to create SettingsService.

    Args:
        session: Database session

    Returns:
        SettingsService instance
    """
    return SettingsService(session)
