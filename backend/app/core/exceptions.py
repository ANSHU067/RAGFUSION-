"""
Custom exceptions and exception handlers.

Provides structured error handling with proper HTTP status codes.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "identifier": str(identifier)},
        )


class ConflictError(AppException):
    """Resource conflict (e.g., duplicate)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class UnauthorizedError(AppException):
    """Authentication required."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(AppException):
    """Permission denied."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ValidationError(AppException):
    """Input validation error."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after},
        )


class ExternalServiceError(AppException):
    """External service error (e.g., OpenAI, ChromaDB)."""

    def __init__(self, service: str, message: str):
        logger.error("External service %s failed: %s", service, message)
        super().__init__(
            message="External service request failed",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )


def create_exception_response(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """Create standardized error response."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.message,
                "details": exc.details,
                "path": str(request.url.path),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            f"AppException: {exc.message}",
            extra={
                "path": request.url.path,
                "status_code": exc.status_code,
                "details": exc.details,
            },
        )
        return create_exception_response(request, exc)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(PydanticValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError | PydanticValidationError
    ) -> JSONResponse:
        errors = []
        for error in exc.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    # Pydantic custom validators may include arbitrary exception
                    # text. Never serialize their msg/input/ctx/url fields.
                    "message": {
                        "missing": "Field required",
                        "int_parsing": "Expected an integer",
                        "float_parsing": "Expected a number",
                        "bool_parsing": "Expected a boolean",
                        "string_type": "Expected a string",
                        "string_too_short": "Value is too short",
                        "string_too_long": "Value is too long",
                        "greater_than_equal": "Value is below the allowed minimum",
                        "less_than_equal": "Value exceeds the allowed maximum",
                        "literal_error": "Value is not an allowed choice",
                        "json_invalid": "Invalid JSON",
                    }.get(error["type"], "Invalid value"),
                    "type": error["type"],
                }
            )

        logger.warning(
            "Validation error",
            extra={"path": request.url.path, "errors": errors},
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Data validation failed",
                    "details": {"errors": errors},
                    "path": str(request.url.path),
                }
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        logger.exception(
            "Database integrity error",
            extra={"path": request.url.path, "error": str(exc)},
        )

        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": {
                    "type": "ConflictError",
                    "message": "Data integrity constraint violated",
                    "details": {},
                    "path": str(request.url.path),
                }
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception(
            "Database error",
            extra={"path": request.url.path, "error": str(exc)},
        )

        detail = "Database operation failed"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "DatabaseError",
                    "message": detail,
                    "details": {},
                    "path": str(request.url.path),
                }
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception",
            extra={"path": request.url.path, "error": str(exc)},
        )

        message = "Internal server error"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "type": "InternalServerError",
                    "message": message,
                    "details": {},
                    "path": str(request.url.path),
                }
            },
        )
