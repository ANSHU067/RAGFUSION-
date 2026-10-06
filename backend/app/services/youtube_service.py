"""YouTube transcript ingestion service."""

from __future__ import annotations

import logging
import threading
import re
import time
import uuid
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse

import anyio
from requests import Session as HTTPSession
from requests.exceptions import Timeout as HTTPTimeout

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:  # Optional integration; non-YouTube chat must still work.
    YouTubeTranscriptApi = None  # type: ignore[assignment,misc]

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory
from app.models.entities import Embedding, SourceStatus, YouTubeSource
from app.rag.retrievers.retriever_manager import RetrieverManager
from app.services.embedding_helper import generate_embeddings

INGEST_LIMITER = anyio.CapacityLimiter(2)


class YouTubeIngestionError(Exception):
    """Raised when YouTube ingestion fails."""

    def __init__(
        self,
        message: str,
        code: str = "YOUTUBE_INGESTION_ERROR",
    ):
        self.message = message
        self.code = code
        super().__init__(message)


def add_youtube_chunks_to_retriever(
    youtube_source_id: uuid.UUID,
    user_id: uuid.UUID,
    video_id: str,
    url: str,
    chunks: list[Any],
) -> None:
    """Add transcript chunks to the shared Chroma RAG collection."""

    source_label = f"YouTube video ({video_id})"
    RetrieverManager().add_documents(
        documents=[chunk.content for chunk in chunks],
        metadatas=[
            {
                "source_id": str(youtube_source_id),
                "source_type": "youtube",
                "youtube_source_id": str(youtube_source_id),
                "user_id": str(user_id),
                "video_id": video_id,
                "youtube_url": url,
                "title": source_label,
                "filename": source_label,
                "chunk_index": chunk.index,
            }
            for chunk in chunks
        ],
        ids=[
            f"{youtube_source_id}_chunk_{chunk.index}"
            for chunk in chunks
        ],
    )


async def ensure_youtube_sources_in_retriever(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """Backfill ready YouTube sources that predate RAG collection indexing."""

    sources = (
        await db.scalars(
            select(YouTubeSource).where(
                YouTubeSource.user_id == user_id,
                YouTubeSource.status == SourceStatus.ready,
            )
        )
    ).all()

    for source in sources:
        if source.metadata_.get("rag_indexed") is True:
            continue

        embeddings = (
            await db.scalars(
                select(Embedding)
                .where(Embedding.youtube_source_id == source.id)
                .order_by(Embedding.chunk_index)
            )
        ).all()

        if not embeddings:
            continue

        chunks = [
            SimpleNamespace(
                index=embedding.chunk_index,
                content=embedding.content,
            )
            for embedding in embeddings
        ]

        try:
            await anyio.to_thread.run_sync(
                add_youtube_chunks_to_retriever,
                source.id,
                user_id,
                source.video_id,
                source.url,
                chunks,
                limiter=INGEST_LIMITER,
            )
        except Exception as exc:
            raise YouTubeIngestionError(
                "YouTube vector indexing failed",
                code="RAG_INDEXING_FAILED",
            ) from exc

        source.metadata_ = {**source.metadata_, "rag_indexed": True}

    await db.commit()


def extract_video_id(url: str) -> str:
    """Extract a YouTube video ID from a YouTube URL."""

    parsed = urlparse(url)

    hostname = parsed.netloc.lower().replace("www.", "")

    # https://www.youtube.com/watch?v=VIDEO_ID
    if hostname in {"youtube.com", "m.youtube.com"}:
        query = parse_qs(parsed.query)
        video_id = query.get("v", [None])[0]

        if video_id:
            return video_id

        # https://youtube.com/shorts/VIDEO_ID
        # https://youtube.com/embed/VIDEO_ID
        # https://youtube.com/live/VIDEO_ID
        parts = [part for part in parsed.path.split("/") if part]

        if len(parts) >= 2 and parts[0] in {
            "shorts",
            "embed",
            "live",
        }:
            return parts[1]

    # https://youtu.be/VIDEO_ID
    if hostname == "youtu.be":
        parts = [part for part in parsed.path.split("/") if part]

        if parts:
            return parts[0]

    raise YouTubeIngestionError(
        "Invalid YouTube URL. Please provide a valid YouTube video URL.",
        code="INVALID_YOUTUBE_URL",
    )


def clean_transcript_text(text: str) -> str:
    """Clean transcript text before chunking."""

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def build_chunks(
    transcript_text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[dict[str, Any]]:
    """
    Split transcript text into overlapping word chunks.

    chunk_size and chunk_overlap are treated as approximate word counts.
    """

    if not transcript_text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    words = transcript_text.split()

    chunks: list[dict[str, Any]] = []

    step = chunk_size - chunk_overlap

    chunk_index = 0

    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]

        if not chunk_words:
            break

        content = " ".join(chunk_words)

        chunks.append(
            {
                "index": chunk_index,
                "content": content,
                "token_count": len(chunk_words),
                "metadata": {
                    "chunk_index": chunk_index,
                    "start_word": start,
                    "end_word": start + len(chunk_words),
                },
            }
        )

        chunk_index += 1

        if start + chunk_size >= len(words):
            break

    return chunks


logger = logging.getLogger(__name__)
TRANSCRIPT_TIMEOUT = 20.0
_TRANSCRIPT_WORKERS = threading.BoundedSemaphore(2)


class TranscriptSession(HTTPSession):
    """Socket deadlines for every fetch, listing, fallback and redirect request."""

    def __init__(self, deadline: float):
        super().__init__()
        self.deadline = deadline
        self.max_redirects = 3

    def send(self, request, **kwargs):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise HTTPTimeout("Transcript deadline exceeded")
        kwargs["timeout"] = (min(3.0, remaining), min(5.0, remaining))
        return super().send(request, **kwargs)


def _fetch_transcript_sync(video_id: str, languages: list[str], deadline: float) -> str:
    # Abandoned callers must not permit an unbounded number of socket workers.
    if not _TRANSCRIPT_WORKERS.acquire(blocking=False):
        raise YouTubeIngestionError("Transcript service is busy", code="TRANSCRIPT_BUSY")
    try:
        with TranscriptSession(deadline) as http:
            api = YouTubeTranscriptApi(http_client=http)
            from youtube_transcript_api import NoTranscriptFound

            try:
                transcript = api.fetch(video_id, languages=languages)
            except NoTranscriptFound:
                # Only language absence permits fallback. Disabled transcripts,
                # timeouts and provider failures must not trigger more requests.
                available = list(api.list(video_id))
                if time.monotonic() >= deadline:
                    raise HTTPTimeout("Transcript deadline exceeded")
                if not available:
                    raise YouTubeIngestionError("No transcript found", code="TRANSCRIPT_NOT_FOUND")
                manual = [item for item in available if not item.is_generated]
                transcript = (manual or available)[0].fetch()
            if time.monotonic() >= deadline:
                raise HTTPTimeout("Transcript deadline exceeded")
            parts = [item.text if hasattr(item, "text") else item.get("text", "") for item in transcript]
            result = clean_transcript_text(" ".join(parts))
            if not result:
                raise YouTubeIngestionError("Transcript is empty", code="EMPTY_TRANSCRIPT")
            return result
    finally:
        _TRANSCRIPT_WORKERS.release()


async def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Bound the entire preferred-language and fallback flow to twenty seconds."""
    if YouTubeTranscriptApi is None:
        raise YouTubeIngestionError("Transcript service unavailable", code="YOUTUBE_TRANSCRIPT_DEPENDENCY_MISSING")
    try:
        with anyio.fail_after(TRANSCRIPT_TIMEOUT):
            return await anyio.to_thread.run_sync(
                _fetch_transcript_sync, video_id, languages or ["en"],
                time.monotonic() + TRANSCRIPT_TIMEOUT, abandon_on_cancel=True,
                limiter=INGEST_LIMITER,
            )
    except (TimeoutError, HTTPTimeout) as exc:
        logger.exception("Transcript request timed out")
        raise YouTubeIngestionError("YouTube transcript request timed out", code="TRANSCRIPT_TIMEOUT") from exc
    except YouTubeIngestionError:
        raise
    except Exception as exc:
        logger.exception("Transcript unavailable")
        raise YouTubeIngestionError("YouTube transcript unavailable", code="TRANSCRIPT_FETCH_FAILED") from exc


async def ingest_youtube(
    url: str,
    user_id: uuid.UUID,
    languages: list[str] | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    embedding_model: str = "text-embedding-3-small",
) -> dict[str, Any]:
    """
    Complete YouTube ingestion pipeline.

    URL
      -> video ID
      -> transcript
      -> chunks
      -> embeddings
      -> database
    """

    start_time = time.time()
    print(f"[YOUTUBE] Starting ingestion: {url}", flush=True)
    
    video_id = extract_video_id(url)
    print(f"[YOUTUBE] Video ID: {video_id}", flush=True)

    # ---------------------------------------------------------
    # Step 1: Check whether this video already exists
    # ---------------------------------------------------------

    async with get_session_factory()() as session:
        existing = await session.scalar(
            __import__("sqlalchemy").select(YouTubeSource).where(
                YouTubeSource.user_id == user_id,
                YouTubeSource.video_id == video_id,
            )
        )

        if existing:
            raise YouTubeIngestionError(
                "This YouTube video has already been added.",
                code="VIDEO_ALREADY_EXISTS",
            )

    # ---------------------------------------------------------
    # Step 2: Fetch transcript
    # ---------------------------------------------------------
    print(
        f"[YOUTUBE] Fetching transcript for {video_id} "
        f"languages={languages or ['en']}",
        flush=True,
    )

    transcript = await fetch_transcript(
        video_id=video_id,
        languages=languages,
    )

    print(
        f"[YOUTUBE] Transcript fetched: {len(transcript)} characters",
        flush=True,
    )

    # ---------------------------------------------------------
    # Step 3: Create YouTube source
    # ---------------------------------------------------------

    youtube_source_id = uuid.uuid4()

    async with get_session_factory()() as session:
        youtube_source = YouTubeSource(
            id=youtube_source_id,
            user_id=user_id,
            video_id=video_id,
            url=url,
            status=SourceStatus.pending,
            metadata_={
                "transcript_language": (
                    languages[0] if languages else "en"
                ),
            },
        )

        session.add(youtube_source)

        await session.commit()

    try:
        # -----------------------------------------------------
        # Step 4: Chunk transcript
        # -----------------------------------------------------
        print("[YOUTUBE] Building chunks...", flush=True)
        chunks = await anyio.to_thread.run_sync(
            build_chunks,
            transcript,
            chunk_size,
            chunk_overlap,
            limiter=INGEST_LIMITER,
        )
        print(
            f"[YOUTUBE] Chunks created: {len(chunks)}",
            flush=True,
        )

        if not chunks:
            raise YouTubeIngestionError(
                "No chunks could be generated from the transcript.",
                code="NO_CHUNKS_GENERATED",
            )

        # -----------------------------------------------------
        # Step 5: Create lightweight chunk objects
        # -----------------------------------------------------

        class TranscriptChunk:
            def __init__(
                self,
                index: int,
                content: str,
                token_count: int,
                metadata: dict[str, Any],
            ):
                self.index = index
                self.content = content
                self.token_count = token_count
                self.metadata = metadata

        chunk_objects = [
            TranscriptChunk(
                index=chunk["index"],
                content=chunk["content"],
                token_count=chunk["token_count"],
                metadata=chunk["metadata"],
            )
            for chunk in chunks
        ]

        # -----------------------------------------------------
        # Step 6: Generate embeddings using existing system
        # -----------------------------------------------------
        print(
            f"[YOUTUBE] Generating embeddings for {len(chunk_objects)} chunks...",
            flush=True,
        )

        embeddings = await generate_embeddings(
            chunk_objects,
            embedding_model,
        )

        print(
            f"[YOUTUBE] Embeddings generated: {len(embeddings)}",
            flush=True,
        )

        if len(embeddings) != len(chunk_objects):
            raise YouTubeIngestionError(
                "Embedding count does not match chunk count.",
                code="EMBEDDING_COUNT_MISMATCH",
            )

        # -----------------------------------------------------
        # Step 7: Store embeddings
        # -----------------------------------------------------
        print("[YOUTUBE] Storing embeddings in database...", flush=True)

        # Mirror YouTube transcript chunks into the same Chroma collection
        # used by the existing document RAG flow. The SQL Embedding rows remain
        # the source of truth for the reader and transcript reconstruction.
        try:
            await anyio.to_thread.run_sync(
                add_youtube_chunks_to_retriever,
                youtube_source_id,
                user_id,
                video_id,
                url,
                chunk_objects,
                limiter=INGEST_LIMITER,
            )
        except Exception as exc:
            raise YouTubeIngestionError(
                "YouTube vector indexing failed",
                code="RAG_INDEXING_FAILED",
            ) from exc
        
        async with get_session_factory()() as session:
            for chunk, embedding in zip(
                chunk_objects,
                embeddings,
            ):
                emb = Embedding(
                    youtube_source_id=youtube_source_id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    vector=embedding,
                    model_name=embedding_model,
                    token_count=chunk.token_count,
                    metadata_={
                        **chunk.metadata,
                        "video_id": video_id,
                        "youtube_url": url,
                    },
                )

                session.add(emb)

            # Update source
            youtube_source = await session.get(
                YouTubeSource,
                youtube_source_id,
            )

            if youtube_source:
                youtube_source.status = SourceStatus.ready

                youtube_source.metadata_ = {
                    **youtube_source.metadata_,
                    "total_chunks": len(chunk_objects),
                    "total_tokens": sum(
                        chunk.token_count
                        for chunk in chunk_objects
                    ),
                    "transcript_characters": len(transcript),
                    "processing_time_ms": int(
                        (time.time() - start_time) * 1000
                    ),
                    "rag_indexed": True,
                }

            await session.commit()
            print("[YOUTUBE] Database commit successful", flush=True)
            print(
                f"[YOUTUBE] INGESTION COMPLETE: {len(chunk_objects)} chunks",
                flush=True,
            )

        return {
            "youtube_source_id": youtube_source_id,
            "video_id": video_id,
            "url": url,
            "status": "ready",
            "total_chunks": len(chunk_objects),
            "total_tokens": sum(
                chunk.token_count
                for chunk in chunk_objects
            ),
        }

    except YouTubeIngestionError:
        await _mark_failed(
            youtube_source_id,
            "YouTube ingestion failed.",
        )
        raise

    except Exception as exc:
        logger.exception("YouTube ingestion failed")
        await _mark_failed(
            youtube_source_id,
            "YouTube ingestion failed",
        )

        raise YouTubeIngestionError(
            "YouTube ingestion failed",
            code="INGESTION_FAILED",
        ) from exc


async def _mark_failed(
    youtube_source_id: uuid.UUID,
    error: str,
) -> None:
    """Mark a YouTube source as failed."""

    async with get_session_factory()() as session:
        source = await session.get(
            YouTubeSource,
            youtube_source_id,
        )

        if source:
            source.status = SourceStatus.failed
            source.metadata_ = {
                **source.metadata_,
                "error": error,
            }

            await session.commit()


async def delete_youtube(
    youtube_source_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Delete a YouTube source and its embeddings."""

    from sqlalchemy import select

    async with get_session_factory()() as session:
        source = await session.scalar(
            select(YouTubeSource).where(
                YouTubeSource.id == youtube_source_id,
                YouTubeSource.user_id == user_id,
            )
        )

        if not source:
            return False

        await session.delete(source)
        await session.commit()

        return True


def remove_youtube_from_retriever(youtube_source_id: uuid.UUID) -> None:
    """Remove a YouTube source's chunks from the shared RAG collection."""

    try:
        RetrieverManager().vectorstore.delete(
            where={"youtube_source_id": str(youtube_source_id)}
        )
    except Exception as exc:
        raise YouTubeIngestionError(
            "YouTube source deletion failed",
            code="RAG_DELETE_FAILED",
        ) from exc
