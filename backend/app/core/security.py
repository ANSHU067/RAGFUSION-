"""Security dependencies, response sanitization, and structured audit logging."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from fastapi import HTTPException, Request, status

from app.core.jwt_manager import JWTManager, TokenValidationError

logger = logging.getLogger("app.security")
T = TypeVar("T")
_SENSITIVE = re.compile(
    r"(?:password|secret|token|api[_-]?key|authorization|credential)", re.IGNORECASE
)


def sanitize_response(value: T) -> T:
    """Redact recursively by sensitive field name before logging or returning data."""
    if isinstance(value, dict):
        return {key: "[REDACTED]" if _SENSITIVE.search(str(key)) else sanitize_response(item) for key, item in value.items()}  # type: ignore[return-value]
    if isinstance(value, list):
        return [sanitize_response(item) for item in value]  # type: ignore[return-value]
    if isinstance(value, tuple):
        return tuple(sanitize_response(item) for item in value)  # type: ignore[return-value]
    return value


def security_event(
    event: str, *, request: Request | None = None, **fields: Any
) -> None:
    """Write a structured security event without exposing credentials."""
    payload = sanitize_response(fields)
    if request:
        payload.update(
            path=request.url.path,
            method=request.method,
            client_ip=request.client.host if request.client else "unknown",
        )
    logger.warning("security_event=%s details=%s", event, payload)


def require_roles(*roles: str) -> Callable[[Request], Awaitable[dict[str, Any]]]:
    """FastAPI dependency factory for role-based authorization."""
    allowed = frozenset(roles)
    if not allowed:
        raise ValueError("at least one role is required")

    async def dependency(request: Request) -> dict[str, Any]:
        claims = getattr(request.state, "auth", None)
        if not claims:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
        if claims.get("role") not in allowed:
            security_event(
                "authorization_denied",
                request=request,
                required_roles=sorted(allowed),
                role=claims.get("role"),
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return claims

    return dependency


def verify_bearer_token(token: str, manager: JWTManager) -> dict[str, Any]:
    try:
        return manager.verify(token)
    except TokenValidationError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Invalid or expired authentication token"
        ) from exc
