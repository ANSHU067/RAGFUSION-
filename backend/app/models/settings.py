"""Database model for user settings."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.entities import User


class LLMProvider(str, enum.Enum):
    """Supported LLM providers."""

    openai = "openai"
    anthropic = "anthropic"
    ollama = "ollama"
    groq = "groq"
    together = "together"
    custom = "custom"


class EmbeddingProvider(str, enum.Enum):
    """Supported embedding providers."""

    openai = "openai"
    huggingface = "huggingface"
    cohere = "cohere"
    voyage = "voyage"
    ollama = "ollama"
    custom = "custom"


class UserSettings(Base):
    """User-specific AI settings configuration."""

    __tablename__ = "user_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_settings_user"),
        CheckConstraint("chunk_overlap >= 0 AND chunk_overlap < chunk_size", name="ck_user_settings_chunk_overlap"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # LLM settings
    provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, native_enum=False), default=LLMProvider.openai, nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(255), default="gpt-4o-mini", nullable=False)

    # Embedding settings
    embedding_provider: Mapped[EmbeddingProvider] = mapped_column(
        Enum(EmbeddingProvider, native_enum=False),
        default=EmbeddingProvider.openai,
        nullable=False,
    )
    embedding_model: Mapped[str] = mapped_column(
        String(255), default="text-embedding-3-small", nullable=False
    )

    # Generation parameters
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)

    # Chunking parameters
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200, nullable=False)

    # Retrieval parameters
    similarity_threshold: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    reranking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationship
    user: Mapped[User] = relationship(back_populates="user_settings")

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id}, provider={self.provider}, model={self.model_name})>"
