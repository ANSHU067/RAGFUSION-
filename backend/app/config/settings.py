"""Typed configuration loaded from the environment."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.config.branding_compat import LEGACY_ENV_PREFIX, LEGACY_DATABASE_URL, default_upload_dir, display_brand


class Settings(BaseSettings):
    """Runtime settings for the API and its backing services."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_prefix="RAGFUSION_",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "RAGFUSION API"
    environment: str = "development"
    debug: bool = False
    DEBUG: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default=LEGACY_DATABASE_URL,
        validation_alias=AliasChoices("RAGFUSION_DATABASE_URL", "DATABASE_URL"),
        min_length=1,
    )
    redis_url: str = "redis://redis:6379/0"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"])
    log_level: str = "INFO"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    trusted_proxies: list[str] = Field(default_factory=list)
    rate_limit_redis_timeout_seconds: float = Field(default=1.0, gt=0, le=5)
    anonymize_telemetry: bool = Field(default=False, validation_alias="ANONYMIZE_TELEMETRY")
    chroma_telemetry: bool = Field(default=False, validation_alias="CHROMA_TELEMETRY")
    embedding_local_files_only: bool = True
    embedding_cache_dir: str | None = None
    embedding_warmup: bool = True

    # Document ingestion
    upload_dir: str = Field(
        default_factory=default_upload_dir, description="Directory for uploaded files"
    )
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")

    @field_validator('app_name')
    @classmethod
    def canonical_brand(cls, value):
        return display_brand(value)


# Canonical names take precedence; existing .env files remain valid. Explicit
# unprefixed aliases (DATABASE_URL and telemetry options) are retained as well.
for _name, _field in Settings.model_fields.items():
    _alias = _field.validation_alias
    _aliases = _alias.choices if isinstance(_alias, AliasChoices) else ([_alias] if _alias else [])
    _field.validation_alias = AliasChoices(*dict.fromkeys([
        'RAGFUSION_' + _name.upper(), LEGACY_ENV_PREFIX + _name.upper(), *_aliases,
    ]))
Settings.model_rebuild(force=True)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application configuration."""

    return Settings()
