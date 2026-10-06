"""Settings request and response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SettingsBase(BaseModel):
    """Base settings schema with validation rules."""

    # LLM settings
    provider: str = Field(
        default="openai",
        description="LLM provider (openai, anthropic, ollama, groq, together, custom)",
        min_length=1,
        max_length=50,
    )
    model_name: str = Field(
        default="gpt-4o-mini",
        description="Model name for the selected provider",
        min_length=1,
        max_length=255,
    )

    # Embedding settings
    embedding_provider: str = Field(
        default="openai",
        description="Embedding provider (openai, huggingface, cohere, voyage, ollama, custom)",
        min_length=1,
        max_length=50,
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name for the selected provider",
        min_length=1,
        max_length=255,
    )

    # Generation parameters
    temperature: float = Field(
        default=0.7,
        description="Sampling temperature (0.0 = deterministic, 2.0 = maximum creativity)",
        ge=0.0,
        le=2.0,
    )
    top_k: int = Field(
        default=5,
        description="Number of documents to retrieve for RAG context",
        ge=1,
        le=100,
    )
    max_tokens: int = Field(
        default=2000,
        description="Maximum tokens in LLM response",
        ge=100,
        le=32000,
    )

    # Chunking parameters
    chunk_size: int = Field(
        default=1000,
        description="Size of text chunks for document processing",
        ge=128,
        le=4096,
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between consecutive chunks",
        ge=0,
    )

    # Retrieval parameters
    similarity_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score for document retrieval (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )
    reranking_enabled: bool = Field(
        default=True,
        description="Enable reranking of retrieved documents",
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info: Any) -> int:
        """Ensure chunk_overlap is less than chunk_size."""
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate LLM provider."""
        valid_providers = {
            "openai",
            "anthropic",
            "ollama",
            "groq",
            "together",
            "custom",
        }
        if v.lower() not in valid_providers:
            raise ValueError(
                f"Invalid provider '{v}'. Must be one of: {', '.join(valid_providers)}"
            )
        return v.lower()

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        """Validate embedding provider."""
        valid_providers = {
            "openai",
            "huggingface",
            "cohere",
            "voyage",
            "ollama",
            "custom",
        }
        if v.lower() not in valid_providers:
            raise ValueError(
                f"Invalid embedding provider '{v}'. Must be one of: {', '.join(valid_providers)}"
            )
        return v.lower()

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v or not v.strip():
            raise ValueError("model_name cannot be empty")
        return v.strip()

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str) -> str:
        """Validate embedding model name is not empty."""
        if not v or not v.strip():
            raise ValueError("embedding_model cannot be empty")
        return v.strip()


class SettingsCreate(SettingsBase):
    """Settings creation schema (all fields optional, defaults applied)."""

    pass


class SettingsUpdate(BaseModel):
    """Settings update schema (all fields optional)."""

    # LLM settings
    provider: str | None = Field(
        default=None,
        description="LLM provider",
        min_length=1,
        max_length=50,
    )
    model_name: str | None = Field(
        default=None,
        description="Model name for the selected provider",
        min_length=1,
        max_length=255,
    )

    # Embedding settings
    embedding_provider: str | None = Field(
        default=None,
        description="Embedding provider",
        min_length=1,
        max_length=50,
    )
    embedding_model: str | None = Field(
        default=None,
        description="Embedding model name",
        min_length=1,
        max_length=255,
    )

    # Generation parameters
    temperature: float | None = Field(
        default=None,
        description="Sampling temperature",
        ge=0.0,
        le=2.0,
    )
    top_k: int | None = Field(
        default=None,
        description="Number of documents to retrieve",
        ge=1,
        le=100,
    )
    max_tokens: int | None = Field(
        default=None,
        description="Maximum tokens in LLM response",
        ge=100,
        le=32000,
    )

    # Chunking parameters
    chunk_size: int | None = Field(
        default=None,
        description="Size of text chunks",
        ge=128,
        le=4096,
    )
    chunk_overlap: int | None = Field(
        default=None,
        description="Overlap between consecutive chunks",
        ge=0,
    )

    # Retrieval parameters
    similarity_threshold: float | None = Field(
        default=None,
        description="Minimum similarity score",
        ge=0.0,
        le=1.0,
    )
    reranking_enabled: bool | None = Field(
        default=None,
        description="Enable reranking",
    )

    @field_validator("chunk_overlap")
    @classmethod
    def validate_chunk_overlap(cls, v: int | None, info: Any) -> int | None:
        """Ensure chunk_overlap is less than chunk_size if both provided."""
        if v is not None:
            chunk_size = info.data.get("chunk_size")
            if chunk_size is not None and v >= chunk_size:
                raise ValueError("chunk_overlap must be less than chunk_size")
        return v

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str | None) -> str | None:
        """Validate LLM provider if provided."""
        if v is not None:
            valid_providers = {
                "openai",
                "anthropic",
                "ollama",
                "groq",
                "together",
                "custom",
            }
            if v.lower() not in valid_providers:
                raise ValueError(
                    f"Invalid provider '{v}'. Must be one of: {', '.join(valid_providers)}"
                )
            return v.lower()
        return v

    @field_validator("embedding_provider")
    @classmethod
    def validate_embedding_provider(cls, v: str | None) -> str | None:
        """Validate embedding provider if provided."""
        if v is not None:
            valid_providers = {
                "openai",
                "huggingface",
                "cohere",
                "voyage",
                "ollama",
                "custom",
            }
            if v.lower() not in valid_providers:
                raise ValueError(
                    f"Invalid embedding provider '{v}'. Must be one of: {', '.join(valid_providers)}"
                )
            return v.lower()
        return v

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str | None) -> str | None:
        """Validate model name is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("model_name cannot be empty")
        return v.strip() if v else v

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: str | None) -> str | None:
        """Validate embedding model name is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("embedding_model cannot be empty")
        return v.strip() if v else v


class SettingsResponse(SettingsBase):
    """Settings response schema with metadata."""

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SettingsResetResponse(BaseModel):
    """Response for settings reset operation."""

    message: str = "Settings reset to defaults successfully"
    settings: SettingsResponse


# Default settings constants for reference
DEFAULT_SETTINGS = {
    "provider": "openai",
    "model_name": "gpt-4o-mini",
    "embedding_provider": "openai",
    "embedding_model": "text-embedding-3-small",
    "temperature": 0.7,
    "top_k": 5,
    "max_tokens": 2000,
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "similarity_threshold": 0.7,
    "reranking_enabled": True,
}
