"""Database entities for users, sources, conversations, and vector chunks."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (JSON, Boolean, DateTime, Enum, Float, ForeignKey,
                        Index, Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.types import UTCDateTime, utc_now

if TYPE_CHECKING:
    from app.models.settings import UserSettings


class SourceStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class MessageRole(str, enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(String(1000))
    workspace: Mapped[str | None] = mapped_column(String(120))
    avatar_color: Mapped[str] = mapped_column(String(16), default='slate', server_default='slate', nullable=False)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.user, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    auth_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    documents: Mapped[list[Document]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    websites: Mapped[list[Website]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    youtube_sources: Mapped[list[YouTubeSource]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    chat_sessions: Mapped[list[ChatSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped[list[Setting]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_settings: Mapped["UserSettings"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(255))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, native_enum=False),
        default=SourceStatus.pending,
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=lambda: {}, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="documents")
    embeddings: Mapped[list[Embedding]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Website(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "websites"
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_websites_user_url"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, native_enum=False),
        default=SourceStatus.pending,
        nullable=False,
    )
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=lambda: {}, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="websites")
    embeddings: Mapped[list[Embedding]] = relationship(
        back_populates="website", cascade="all, delete-orphan"
    )


class YouTubeSource(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "youtube_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "video_id", name="uq_youtube_sources_user_video"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    video_id: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    channel_name: Mapped[str | None] = mapped_column(String(255))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, native_enum=False),
        default=SourceStatus.pending,
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=lambda: {}, nullable=False
    )

    user: Mapped[User] = relationship(back_populates="youtube_sources")
    embeddings: Mapped[list[Embedding]] = relationship(
        back_populates="youtube_source", cascade="all, delete-orphan"
    )


class ChatSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New chat", nullable=False)
    session_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=lambda: {}, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    user: Mapped[User] = relationship(back_populates="chat_sessions")
    messages: Mapped[list[Message]] = relationship(
        back_populates="chat_session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, native_enum=False), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    token_count: Mapped[int | None] = mapped_column(Integer)

    chat_session: Mapped[ChatSession] = relationship(back_populates="messages")


class Setting(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_settings_user_key"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)

    user: Mapped[User] = relationship(back_populates="settings")


class Embedding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_embeddings_document_chunk"),
        Index("ix_embeddings_document_chunk", "document_id", "chunk_index"),
        Index("ix_embeddings_website_chunk", "website_id", "chunk_index"),
        Index("ix_embeddings_youtube_chunk", "youtube_source_id", "chunk_index"),
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=True
    )
    website_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("websites.id", ondelete="CASCADE"), nullable=True
    )
    youtube_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("youtube_sources.id", ondelete="CASCADE"), nullable=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    vector: Mapped[list[float]] = mapped_column(JSON, nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=lambda: {}, nullable=False
    )

    document: Mapped[Document | None] = relationship(back_populates="embeddings")
    website: Mapped[Website | None] = relationship(back_populates="embeddings")
    youtube_source: Mapped[YouTubeSource | None] = relationship(
        back_populates="embeddings"
    )
