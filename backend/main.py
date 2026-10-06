"""FastAPI application entry point."""

from fastapi import FastAPI
import asyncio
import logging
import anyio
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import router
from app.config.settings import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.performance import PerformanceMiddleware
from app.core.environment import SecurityEnvironment
from app.db.session import dispose_engines
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.async_executor import AsyncExecutor
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.core.rate_limiter import RateLimiter, RedisRateLimiter


def create_app(*, rate_limiter: RateLimiter | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()
    configure_logging()
    # Debug middleware otherwise bypasses sanitized handlers with tracebacks.
    app = FastAPI(title=settings.app_name, debug=False)
    app.state.async_executor = AsyncExecutor()
    app.state.rag_pipeline = None
    app.state.rag_pipeline_lock = asyncio.Lock()
    app.state.rate_limiter = rate_limiter if rate_limiter is not None else RedisRateLimiter(
        settings.redis_url, timeout=settings.rate_limit_redis_timeout_seconds
    )
    security_environment = SecurityEnvironment(
        environment=settings.environment,
        jwt_secret=settings.jwt_secret_key,
        jwt_algorithm=settings.jwt_algorithm,
        cors_origins=tuple(settings.cors_origins),
    )
    security_environment.validate()
    app.add_middleware(GZipMiddleware, minimum_size=1_000)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(
        RateLimitMiddleware, trusted_proxies=tuple(settings.trusted_proxies),
        api_prefix=settings.api_v1_prefix,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware, environment=security_environment)
    app.include_router(router, prefix=settings.api_v1_prefix)
    register_exception_handlers(app)

    @app.on_event("startup")
    async def warm_embedding_model() -> None:
        if settings.embedding_warmup:
            from app.core.embedding_runtime import MODEL_LIMITER, get_sentence_transformer

            try:
                await anyio.to_thread.run_sync(get_sentence_transformer, limiter=MODEL_LIMITER)
            except Exception:
                # Authentication and health remain usable when an operator has
                # not provisioned the local model cache yet.
                logging.getLogger(__name__).exception("Local embedding model unavailable")

    @app.on_event("shutdown")
    async def release_performance_resources() -> None:
        await app.state.async_executor.shutdown()
        await app.state.rate_limiter.aclose()
        await dispose_engines()

    return app


app = create_app()
