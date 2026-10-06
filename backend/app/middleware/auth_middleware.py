"""Bearer-token authentication middleware and route protection controls."""

from __future__ import annotations

from collections.abc import Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.jwt_manager import JWTManager, TokenValidationError
from app.core.security import security_event


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Validate Bearer tokens before protected endpoints receive a request."""

    def __init__(
        self,
        app,
        *,
        jwt_manager: JWTManager,
        public_paths: Iterable[str] = (
            "/docs",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/signup",
            "/api/v1/auth/refresh",
        ),
    ) -> None:
        super().__init__(app)
        self.jwt_manager = jwt_manager
        self.public_paths = frozenset(public_paths)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method == "OPTIONS" or request.url.path in self.public_paths:
            return await call_next(request)
        value = request.headers.get("Authorization", "")
        if not value.startswith("Bearer ") or len(value) <= 7:
            security_event(
                "authentication_failed", request=request, reason="missing_bearer_token"
            )
            return JSONResponse(
                {"error": {"message": "Authentication required"}},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            request.state.auth = self.jwt_manager.verify(value[7:])
        except TokenValidationError:
            security_event(
                "authentication_failed", request=request, reason="invalid_token"
            )
            return JSONResponse(
                {"error": {"message": "Invalid or expired authentication token"}},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        return await call_next(request)
