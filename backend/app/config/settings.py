"""Typed configuration loaded from the environment."""

from functools import lru_cache
import os
import logging
from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.config.branding_compat import LEGACY_ENV_PREFIX, LEGACY_DATABASE_URL, default_upload_dir, display_brand


def normalize_groq_api_key(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


GROQ_KEY_ALIASES = ("RAGFUSION_GROQ_API_KEY", "DOCPRO_GROQ_API_KEY", "GROQ_API_KEY")


def _with_groq_key_selection(source):
    """Keep normal source precedence, but skip empty/invalid key aliases."""
    def read():
        data = source()
        candidates = [normalize_groq_api_key(value) for alias in GROQ_KEY_ALIASES
                      if isinstance(value := source.env_vars.get(
                          alias if source.case_sensitive else alias.lower()), str)]
        if candidates:
            valid = [key for key in candidates if key.startswith("gsk_") and len(key) > 4]
            selected = next(iter(valid or [key for key in candidates if key]), "")
            for alias in (*GROQ_KEY_ALIASES, "groq_api_key"):
                data.pop(alias, None)
            data[GROQ_KEY_ALIASES[0]] = selected
        return data
    return read


def configure_groq_environment(settings, *, log_status: bool = False) -> None:
    os.environ["GROQ_API_KEY"] = settings.groq_api_key
    if log_status:
        logger = logging.getLogger(__name__)
        if settings.groq_api_key.startswith("gsk_") and len(settings.groq_api_key) > 4:
            # No characters from the secret itself are included in logs.
            logger.info("Loaded Groq API key: gsk_****... (len=%d)", len(settings.groq_api_key))
        else:
            logger.warning("Groq API key missing or has an invalid format")


class Settings(BaseSettings):
    """Runtime settings for the API and its backing services."""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        env_prefix="RAGFUSION_",
        extra="ignore",
        populate_by_name=True,
    )

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings,
                                   dotenv_settings, file_secret_settings):
        return (init_settings, _with_groq_key_selection(env_settings),
                _with_groq_key_selection(dotenv_settings), file_secret_settings)

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
    database_connect_timeout_seconds: float = Field(default=20.0, ge=10, le=120)
    groq_api_key: str = Field(
        default="", repr=False,
        validation_alias=AliasChoices("RAGFUSION_GROQ_API_KEY", "DOCPRO_GROQ_API_KEY", "GROQ_API_KEY"),
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
    # Reuse cached ONNX files, downloading them on first use when absent.
    # Offline-only mode is opt-in for deployments with a provisioned cache.
    embedding_local_files_only: bool = False
    embedding_cache_dir: str = Field(
        default_factory=lambda: str(
            Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
            / "ragfusion" / "fastembed"
        ),
        min_length=1,
    )
    # Low-memory hosts load the singleton on first use, in a bounded worker.
    embedding_warmup: bool = False

    # Document ingestion
    upload_dir: str = Field(
        default_factory=default_upload_dir, description="Directory for uploaded files"
    )
    max_file_size_mb: int = Field(default=15, gt=0, description="Document size in MiB; hard ceiling 15 MiB")

    @field_validator("groq_api_key", mode="before")
    @classmethod
    def clean_groq_api_key(cls, value):
        return normalize_groq_api_key(value) if isinstance(value, str) else value

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
