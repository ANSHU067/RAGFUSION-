"""Top-level HTTP routes."""

from fastapi import APIRouter, Request

from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.history import router as history_router
from app.api.settings import router as settings_router
from app.api.youtube import router as youtube_router
from app.api.website import router as website_router
from app.api.dashboard import router as dashboard_router
from app.dependencies.settings import SettingsDependency
from app.schemas.health import HealthResponse
from app.services.health import get_health_status

router = APIRouter(tags=["system"])
router.include_router(auth_router)
router.include_router(chat_router)
router.include_router(documents_router)
router.include_router(history_router)
router.include_router(settings_router)
router.include_router(youtube_router)
router.include_router(website_router)
router.include_router(dashboard_router)


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Report API dependency readiness."""

    # The application owns this client and closes it through the rate limiter.
    # An injected in-memory limiter has no Redis dependency to probe.
    redis_client = getattr(request.app.state.rate_limiter, "redis", None)
    return HealthResponse.model_validate(await get_health_status(redis_client))


@router.get("/info")
def application_info(settings: SettingsDependency) -> dict[str, str]:
    """Expose non-sensitive configuration through FastAPI dependency injection."""

    return {"name": settings.app_name, "environment": settings.environment}
