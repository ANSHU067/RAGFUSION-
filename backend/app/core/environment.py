"""Validated security configuration sourced from the process environment."""

from __future__ import annotations

from app.config.branding_compat import environment_value, JWT_ISSUER, JWT_AUDIENCE
from dataclasses import dataclass


class EnvironmentValidationError(RuntimeError):
    """Raised when an unsafe or incomplete production configuration is used."""


def _csv(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = environment_value(name)
    return (
        tuple(part.strip() for part in value.split(",") if part.strip())
        if value
        else default
    )


@dataclass(frozen=True, slots=True)
class SecurityEnvironment:
    """Security-specific settings with conservative, explicit defaults."""

    environment: str = "development"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = JWT_ISSUER
    jwt_audience: str = JWT_AUDIENCE
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None
    encryption_key: str | None = None
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    cors_methods: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    cors_headers: tuple[str, ...] = (
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
    )
    cors_credentials: bool = True

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @classmethod
    def from_environment(cls) -> "SecurityEnvironment":
        return cls(
            environment=environment_value(
                "RAGFUSION_ENVIRONMENT", environment_value("ENVIRONMENT", "development")
            ),
            jwt_secret=environment_value(
                "RAGFUSION_JWT_SECRET_KEY",
                environment_value("JWT_SECRET", "change-me-in-production"),
            ),
            jwt_algorithm=environment_value("RAGFUSION_JWT_ALGORITHM", "HS256").upper(),
            jwt_issuer=environment_value("RAGFUSION_JWT_ISSUER", JWT_ISSUER),
            jwt_audience=environment_value("RAGFUSION_JWT_AUDIENCE", JWT_AUDIENCE),
            jwt_private_key=environment_value("RAGFUSION_JWT_PRIVATE_KEY"),
            jwt_public_key=environment_value("RAGFUSION_JWT_PUBLIC_KEY"),
            encryption_key=environment_value("RAGFUSION_ENCRYPTION_KEY"),
            cors_origins=_csv("RAGFUSION_CORS_ORIGINS", ("http://localhost:5173",)),
            cors_methods=_csv(
                "RAGFUSION_CORS_METHODS",
                ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
            ),
            cors_headers=_csv(
                "RAGFUSION_CORS_HEADERS",
                ("Authorization", "Content-Type", "X-API-Key", "X-Request-ID"),
            ),
            cors_credentials=environment_value("RAGFUSION_CORS_CREDENTIALS", "true").lower()
            == "true",
        )

    def validate(self, *, require_encryption: bool = False) -> None:
        """Fail fast before accepting production traffic."""
        errors: list[str] = []
        if self.jwt_algorithm not in {"HS256", "RS256"}:
            errors.append("RAGFUSION_JWT_ALGORITHM must be HS256 or RS256")
        if (
            self.production
            and self.jwt_secret in {"", "change-me-in-production"}
            and self.jwt_algorithm == "HS256"
        ):
            errors.append(
                "RAGFUSION_JWT_SECRET_KEY must be set to a strong secret in production"
            )
        if self.jwt_algorithm == "RS256" and (
            not self.jwt_private_key or not self.jwt_public_key
        ):
            errors.append(
                "RS256 requires RAGFUSION_JWT_PRIVATE_KEY and RAGFUSION_JWT_PUBLIC_KEY"
            )
        if self.production and (not self.cors_origins or "*" in self.cors_origins):
            errors.append(
                "production CORS origins must be explicit and must not include '*'"
            )
        if self.cors_credentials and "*" in self.cors_origins:
            errors.append("credentialed CORS cannot use wildcard origins")
        if require_encryption and not self.encryption_key:
            errors.append("RAGFUSION_ENCRYPTION_KEY is required")
        if errors:
            raise EnvironmentValidationError("; ".join(errors))
