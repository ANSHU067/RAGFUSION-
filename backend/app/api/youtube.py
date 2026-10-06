"""YouTube ingestion API routes."""

from __future__ import annotations

import uuid
import logging
import anyio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id as get_current_user
from app.db.session import get_db_session
from app.models.entities import Embedding, SourceStatus, User, YouTubeSource
from app.schemas.youtube import (
    YouTubeDeleteResponse,
    YouTubeIngestRequest,
    YouTubeIngestResponse,
    YouTubeListResponse,
    YouTubeResponse,
)
from app.services.youtube_service import (
    YouTubeIngestionError,
    ingest_youtube,
    remove_youtube_from_retriever,
    INGEST_LIMITER,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/youtube", tags=["youtube"])


def youtube_status(source_status: SourceStatus) -> str:
    """Convert database status to API string."""
    return source_status.value


@router.post(
    "/ingest",
    response_model=YouTubeIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a YouTube video",
)
async def ingest_youtube_route(
    request: YouTubeIngestRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> YouTubeIngestResponse:
    """Ingest a YouTube video transcript into the RAG system."""

    url = str(request.url)

    try:
        result = await ingest_youtube(
            url=url,
            user_id=current_user.id,
            languages=request.languages,
        )

        return YouTubeIngestResponse(
            youtube_source_id=result["youtube_source_id"],
            video_id=result["video_id"],
            url=result["url"],
            title=result.get("title"),
            channel_name=result.get("channel_name"),
            status=result["status"],
            total_chunks=result.get("total_chunks", 0),
            message=result.get(
                "message",
                "YouTube video ingested successfully.",
            ),
        )

    except YouTubeIngestionError as e:
        logger.exception("YouTube ingestion failed")
        raise HTTPException(
            status_code=504 if e.code == "TRANSCRIPT_TIMEOUT" else 400,
            detail="YouTube transcript request timed out" if e.code == "TRANSCRIPT_TIMEOUT" else "YouTube transcript unavailable or ingestion failed",
        )

    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.exception("YouTube ingestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="YouTube ingestion failed",
        )


@router.get(
    "",
    response_model=YouTubeListResponse,
    summary="List user's YouTube sources",
)
async def list_youtube_sources(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> YouTubeListResponse:
    """List all YouTube videos belonging to the current user."""

    query = (
        select(YouTubeSource)
        .where(YouTubeSource.user_id == current_user.id)
        .order_by(YouTubeSource.created_at.desc())
    )

    result = await db.execute(query)
    sources = result.scalars().all()

    items = [
        YouTubeResponse(
            id=source.id,
            video_id=source.video_id,
            url=source.url,
            title=source.title,
            channel_name=source.channel_name,
            duration_seconds=source.duration_seconds,
            status=youtube_status(source.status),
            metadata=source.metadata_,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )
        for source in sources
    ]

    return YouTubeListResponse(
        items=items,
        total=len(items),
        page=1,
        page_size=len(items),
        total_pages=1 if items else 0,
    )


@router.get(
    "/{youtube_source_id}",
    response_model=YouTubeResponse,
    summary="Get YouTube source details",
)
async def get_youtube_source(
    youtube_source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> YouTubeResponse:
    """Get a YouTube source belonging to the current user."""

    query = select(YouTubeSource).where(
        YouTubeSource.id == youtube_source_id,
        YouTubeSource.user_id == current_user.id,
    )

    result = await db.execute(query)
    source = result.scalar_one_or_none()

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="YouTube source not found",
        )

    return YouTubeResponse(
        id=source.id,
        video_id=source.video_id,
        url=source.url,
        title=source.title,
        channel_name=source.channel_name,
        duration_seconds=source.duration_seconds,
        status=youtube_status(source.status),
        metadata=source.metadata_,
        created_at=source.created_at,
        updated_at=source.updated_at,
    )


@router.get("/{youtube_source_id}/transcript")
async def get_youtube_transcript(
    youtube_source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    """Return the reconstructed transcript for a YouTube source."""

    youtube_source = await db.scalar(
        select(YouTubeSource).where(
            YouTubeSource.id == youtube_source_id,
            YouTubeSource.user_id == current_user.id,
        )
    )

    if not youtube_source:
        raise HTTPException(
            status_code=404,
            detail="YouTube source not found.",
        )

    embeddings = (
        await db.scalars(
            select(Embedding)
            .where(
                Embedding.youtube_source_id == youtube_source_id
            )
            .order_by(Embedding.chunk_index)
        )
    ).all()

    if not embeddings:
        raise HTTPException(
            status_code=404,
            detail="No transcript chunks found for this video.",
        )

    # Reconstruct transcript while removing overlapping words.
    transcript_words: list[str] = []
    current_end_word = 0

    for embedding in embeddings:
        metadata = embedding.metadata_ or {}

        start_word = int(metadata.get("start_word", 0))
        content_words = embedding.content.split()

        skip_words = max(
            0,
            current_end_word - start_word,
        )

        transcript_words.extend(content_words[skip_words:])

        current_end_word = max(
            current_end_word,
            int(
                metadata.get(
                    "end_word",
                    start_word + len(content_words),
                )
            ),
        )

    transcript = " ".join(transcript_words)

    return {
        "transcript": transcript,
        "summary": None,
        "video_id": youtube_source.video_id,
        "youtube_source_id": str(youtube_source.id),
        "language": youtube_source.metadata_.get(
            "transcript_language",
            "unknown",
        ),
    }


@router.delete(
    "/{youtube_source_id}",
    response_model=YouTubeDeleteResponse,
    summary="Delete a YouTube source",
)
async def delete_youtube_source(
    youtube_source_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> YouTubeDeleteResponse:
    """Delete a YouTube source and its embeddings."""

    query = select(YouTubeSource).where(
        YouTubeSource.id == youtube_source_id,
        YouTubeSource.user_id == current_user.id,
    )

    result = await db.execute(query)
    source = result.scalar_one_or_none()

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="YouTube source not found",
        )

    try:
        await anyio.to_thread.run_sync(
            remove_youtube_from_retriever, youtube_source_id, limiter=INGEST_LIMITER
        )
    except YouTubeIngestionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="YouTube source deletion failed",
        ) from exc

    await db.delete(source)
    await db.commit()

    return YouTubeDeleteResponse(
        youtube_source_id=youtube_source_id,
        message="YouTube source and associated embeddings deleted successfully.",
    )
