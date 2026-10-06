"""Owned website ingestion; relational readiness gates all vector retrieval."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import anyio
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.entities import Embedding, SourceStatus, Website
from app.rag.retrievers.retriever_manager import RetrieverManager
from app.schemas.document import ChunkingConfig
from app.services.crawler_service import crawl_single_page
from app.services.document import INGEST_LIMITER, chunk_text
from app.services.embedding_helper import generate_embeddings

logger = logging.getLogger(__name__)
WEBSITE_LIMITER = anyio.CapacityLimiter(2)
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def store_vectors(source_id: UUID, owner_id: UUID, url: str, title: str, chunks, vectors):
    """Store already-computed shared-model embeddings without a second embed pass."""
    collection = RetrieverManager().client.get_collection("rag_documents")
    where = {"$and": [{"website_id": str(source_id)}, {"user_id": str(owner_id)}]}
    collection.delete(where=where)
    collection.upsert(
        ids=[f"website:{source_id}:{chunk.index}" for chunk in chunks],
        documents=[chunk.content for chunk in chunks],
        embeddings=vectors,
        metadatas=[{
            "source_id": str(source_id), "website_id": str(source_id),
            "source_type": "website", "user_id": str(owner_id),
            "url": url, "title": title, "chunk_index": chunk.index,
        } for chunk in chunks],
    )


def remove_vectors(source_id: UUID, owner_id: UUID):
    RetrieverManager().client.get_collection("rag_documents").delete(
        where={"$and": [{"website_id": str(source_id)}, {"user_id": str(owner_id)}]}
    )


async def process_website(db: AsyncSession, source_id: UUID, owner_id: UUID) -> Website:
    # Conditional update admits exactly one processor, including across workers.
    claimed = await db.scalar(update(Website).where(
        Website.id == source_id, Website.user_id == owner_id,
        Website.status.in_([SourceStatus.pending, SourceStatus.failed]),
    ).values(status=SourceStatus.processing).returning(Website.id))
    if claimed is None:
        await db.rollback()
        raise AppException("Website is already ready or processing", status_code=409)
    await db.commit()
    source = await db.get(Website, source_id, populate_existing=True)
    original_metadata = dict(source.metadata_)

    async def stage(name: str):
        source.metadata_ = {**source.metadata_, "stage": name}
        await db.commit()

    try:
        async with asyncio.timeout(120), WEBSITE_LIMITER:
            await stage("crawling")
            page = await crawl_single_page(source.url, timeout_seconds=30)
            if page.error or not page.text_content.strip():
                raise AppException("Page could not be read. Use a public HTML URL without redirects.", status_code=400)
            await stage("chunking")
            config = ChunkingConfig.model_validate(source.metadata_.get("chunking", {"strategy": "fixed"}))
            chunks = await anyio.to_thread.run_sync(chunk_text, page.text_content, config, limiter=INGEST_LIMITER)
            if not chunks or len(chunks) > 1000:
                raise AppException("Page content exceeds the supported chunk limit", status_code=400)
            await stage("embedding")
            vectors = await generate_embeddings(chunks, MODEL, dimensions=384)
            if len(vectors) != len(chunks):
                raise RuntimeError("Embedding count mismatch")
            await stage("storing")
            title = (page.metadata.title if page.metadata else None) or source.url
            await anyio.to_thread.run_sync(
                store_vectors, source.id, owner_id, source.url, title[:512], chunks, vectors,
                limiter=INGEST_LIMITER,
            )
            await db.execute(delete(Embedding).where(Embedding.website_id == source.id))
            db.add_all([Embedding(
                website_id=source.id, chunk_index=chunk.index, content=chunk.content,
                vector=vector, model_name=MODEL, token_count=chunk.token_count,
                metadata_={"url": source.url, "user_id": str(owner_id)},
            ) for chunk, vector in zip(chunks, vectors, strict=True)])
            source.title = title[:512]
            source.status = SourceStatus.ready
            source.last_crawled_at = datetime.now(timezone.utc)
            source.metadata_ = {**source.metadata_, "stage": "ready", "total_chunks": len(chunks)}
            await db.commit()
            await db.refresh(source)
            return source
    except (Exception, asyncio.CancelledError) as exc:
        logger.exception("Website ingestion failed", extra={"website_id": str(source_id)})
        # Shield only the failure bookkeeping; a canceled request must not leave
        # a source falsely ready. Leftover vectors remain invisible to retrieval.
        with anyio.CancelScope(shield=True):
            await db.rollback()
            await db.execute(update(Website).where(Website.id == source_id, Website.user_id == owner_id).values(
                status=SourceStatus.failed, metadata_={**original_metadata, "stage": "failed"},
            ))
            await db.commit()
        if isinstance(exc, (AppException, asyncio.CancelledError)):
            raise
        if isinstance(exc, TimeoutError):
            raise AppException("Website processing timed out", status_code=504) from exc
        raise AppException("Website processing failed", status_code=502) from exc
