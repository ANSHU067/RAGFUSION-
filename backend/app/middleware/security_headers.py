"""CORS policy and browser-facing defense-in-depth headers."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.environment import SecurityEnvironment


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Set response security headers and enforce configured CORS origins."""

    def __init__(self, app, *, environment: SecurityEnvironment) -> None:
        super().__init__(app)
        environment.validate()
        self.environment = environment

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")
        allowed = origin in self.environment.cors_origins
        if request.method == "OPTIONS" and origin:
            if not allowed:
                return Response(status_code=403)
            response = Response(status_code=204)
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
        "default-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if self.environment.production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if origin and allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                self.environment.cors_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                self.environment.cors_headers
            )
            if self.environment.cors_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"
        return response
