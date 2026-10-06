"""Authenticated, bounded website ingestion and source management."""
from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.core.exceptions import AppException
from app.db.session import get_db_session
from app.models.entities import SourceStatus, Website
from app.schemas.website import WebsiteResponse, WebsiteListResponse, WebsiteSubmission
from app.services.crawler_service import CrawlerValidationError, validate_url
from app.services.document import INGEST_LIMITER
from app.services.website_service import process_website, remove_vectors

router = APIRouter(prefix="/website", tags=["website"])


def response(source: Website) -> WebsiteResponse:
    stage = source.metadata_.get("stage", "crawling") if source.status == SourceStatus.processing else source.status.value
    return WebsiteResponse(
        id=source.id, url=source.url, title=source.title, status=stage,
        metadata=source.metadata_, last_crawled_at=source.last_crawled_at,
        created_at=source.created_at, updated_at=source.updated_at,
    )


async def owned(db, source_id, owner_id, *, lock=False):
    stmt = select(Website).where(Website.id == source_id, Website.user_id == owner_id)
    if lock:
        stmt = stmt.with_for_update()
    source = await db.scalar(stmt)
    if source is None:
        raise AppException("Website not found", status_code=404)
    return source


@router.post("/ingest", response_model=WebsiteResponse, status_code=201)
async def create_website(request: WebsiteSubmission, user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    url = str(request.url).split("#", 1)[0]
    try:
        validate_url(url)
    except CrawlerValidationError as exc:
        raise AppException("Only public HTTP or HTTPS destinations are allowed", status_code=422) from exc
    source = Website(user_id=user.id, url=url, status=SourceStatus.pending,
                     metadata_={"stage": "pending", "chunking": request.chunking.model_dump()})
    db.add(source)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise AppException("This website has already been added", status_code=409) from exc
    await db.refresh(source)
    return response(source)


@router.get("", response_model=WebsiteListResponse)
async def list_websites(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100),
                        user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    total = await db.scalar(select(func.count()).select_from(Website).where(Website.user_id == user.id))
    rows = await db.scalars(select(Website).where(Website.user_id == user.id)
                            .order_by(Website.created_at.desc(), Website.id).offset((page - 1) * page_size).limit(page_size))
    return WebsiteListResponse(items=[response(row) for row in rows], total=total, page=page,
                               page_size=page_size, total_pages=(total + page_size - 1) // page_size)


@router.get("/{source_id}", response_model=WebsiteResponse)
async def get_website(source_id: UUID, user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    return response(await owned(db, source_id, user.id))


@router.post("/{source_id}/process", response_model=WebsiteResponse)
async def process(source_id: UUID, user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    await owned(db, source_id, user.id)
    return response(await process_website(db, source_id, user.id))


@router.delete("/{source_id}", status_code=204)
async def remove(source_id: UUID, user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    source = await owned(db, source_id, user.id, lock=True)
    if source.status == SourceStatus.processing:
        raise AppException("Wait for website processing to finish", status_code=409)
    try:
        await anyio.to_thread.run_sync(remove_vectors, source.id, user.id, limiter=INGEST_LIMITER)
    except Exception as exc:
        raise AppException("Website deletion failed", status_code=502) from exc
    await db.delete(source)
    await db.commit()
