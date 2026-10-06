"""YouTube ingestion API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class YouTubeIngestRequest(BaseModel):
    """Request to ingest a YouTube video."""

    url: HttpUrl = Field(..., description="YouTube video URL")
    languages: list[str] = Field(
        default_factory=lambda: ["en"],
        description="Preferred transcript languages",
    )


class YouTubeIngestResponse(BaseModel):
    """Response after YouTube ingestion."""

    youtube_source_id: uuid.UUID
    video_id: str
    url: str
    title: str | None = None
    channel_name: str | None = None
    status: str
    total_chunks: int = 0
    message: str


class YouTubeResponse(BaseModel):
    """YouTube source details."""

    id: uuid.UUID
    video_id: str
    url: str
    title: str | None = None
    channel_name: str | None = None
    duration_seconds: int | None = None
    status: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class YouTubeListResponse(BaseModel):
    """Paginated YouTube sources."""

    items: list[YouTubeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class YouTubeDeleteResponse(BaseModel):
    """Response after deleting a YouTube source."""

    youtube_source_id: uuid.UUID
    message: str
