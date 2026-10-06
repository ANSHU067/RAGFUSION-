"""Settings API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.db.session import get_db_session
from app.schemas.auth import UserResponse
from app.schemas.settings import (
    SettingsResetResponse,
    SettingsResponse,
    SettingsUpdate,
)
from app.services.settings_service import (
    SettingsNotFoundError,
    SettingsService,
    SettingsValidationError,
    create_settings_service,
)

router = APIRouter(prefix="/settings", tags=["settings"])


def get_settings_service(
    db: AsyncSession = Depends(get_db_session),
) -> SettingsService:
    """Dependency to get settings service."""
    return create_settings_service(db)


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get user settings",
    description="Retrieve current AI settings for the authenticated user. Creates default settings if none exist.",
)
async def get_settings(
    current_user: UserResponse = Depends(get_current_user_id),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    """Get current user's settings."""
    return await service.get_settings(current_user.id)


@router.put(
    "",
    response_model=SettingsResponse,
    summary="Update user settings",
    description="Update AI settings for the authenticated user. Only provided fields are updated; others remain unchanged.",
)
async def update_settings(
    updates: SettingsUpdate,
    current_user: UserResponse = Depends(get_current_user_id),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResponse:
    """Update user settings."""
    try:
        return await service.update_settings(current_user.id, updates)
    except SettingsValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid settings configuration",
        )
    except SettingsNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found",
        )


@router.post(
    "/reset",
    response_model=SettingsResetResponse,
    summary="Reset user settings",
    description="Reset all AI settings to default values for the authenticated user.",
)
async def reset_settings(
    current_user: UserResponse = Depends(get_current_user_id),
    service: SettingsService = Depends(get_settings_service),
) -> SettingsResetResponse:
    """Reset user settings to defaults."""
    try:
        return await service.reset_settings(current_user.id)
    except SettingsNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Settings not found",
        )
