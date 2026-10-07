"""Chat request and response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, model_validator


class Citation(BaseModel):
    """Citation information for a source."""

    source_id: UUID
    source_type: str = Field(..., description="Type: document, website, youtube")
    content: str = Field(..., description="Relevant content snippet")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source_name: str | None = Field(default=None, description="Display name of the originating source")
    title: str | None = None
    filename: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MessageBase(BaseModel):
    """Base message schema."""

    role: str = Field(..., description="Role: system, user, or assistant")
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    """Message creation schema."""

    pass


class MessageResponse(MessageBase):
    """Message response schema."""

    id: UUID
    chat_session_id: UUID
    citations: list[Citation] = Field(default_factory=list)
    token_count: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceSelection(BaseModel):
    """An optional subset of the authenticated user's indexed sources."""

    model_config = {"extra": "forbid"}
    document: list[UUID] = Field(default_factory=list, max_length=100)
    website: list[UUID] = Field(default_factory=list, max_length=100)
    youtube: list[UUID] = Field(default_factory=list, max_length=100)


class ChatRequest(BaseModel):
    """Chat request schema."""

    message: str = Field(..., min_length=1, max_length=10000)
    session_id: UUID | None = Field(
        default=None, description="Existing session ID or null for new session",
        validation_alias=AliasChoices('chat_session_id', 'session_id'),
    )
    max_tokens: int | None = Field(default=None, ge=100, le=4000)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_k: int | None = Field(
        default=None, ge=1, le=20, description="Number of documents to retrieve"
    )
    include_sources: bool = Field(default=True, description="Include source citations")
    stream: bool = Field(default=False, description="Enable streaming response")
    source_ids: SourceSelection | None = None

    @model_validator(mode='before')
    @classmethod
    def unambiguous_session(cls, values):
        if isinstance(values, dict) and 'chat_session_id' in values and 'session_id' in values:
            if values['chat_session_id'] != values['session_id']:
                raise ValueError('Provide only one conversation ID')
        return values


class ChatResponse(BaseModel):
    """Chat response schema."""

    session_id: UUID
    message: MessageResponse
    sources: list[Citation] = Field(default_factory=list)
    token_usage: dict[str, int] | None = None
    processing_time_ms: float | None = None


class StreamChunk(BaseModel):
    """Streaming response chunk."""

    type: str = Field(
        ..., description="Chunk type: content, citation, metadata, done, error"
    )
    content: str | None = None
    citation: Citation | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None


class ChatSessionCreate(BaseModel):
    """Chat session creation schema."""

    title: str = Field(default="New chat", max_length=255)
    session_metadata: dict[str, Any] = Field(default_factory=dict)


class ChatSessionResponse(BaseModel):
    """Chat session response schema."""

    id: UUID
    user_id: UUID
    title: str
    session_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""

    sessions: list[ChatSessionResponse]
    total: int


class ChatHistoryResponse(BaseModel):
    """Chat history response schema."""

    session: ChatSessionResponse
    messages: list[MessageResponse]
