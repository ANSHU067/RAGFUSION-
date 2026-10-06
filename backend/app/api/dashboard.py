"""Tenant-scoped overview counts and recent conversation aggregates."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.auth import get_current_user_id
from app.db.session import get_db_session
from app.models.entities import Document, Website, YouTubeSource, ChatSession, Message, SourceStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def overview(user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    def ready_count(model):
        return select(func.count()).select_from(model).where(model.user_id == user.id, model.status == SourceStatus.ready).scalar_subquery()
    active = select(func.count()).select_from(ChatSession).where(
        ChatSession.user_id == user.id, ChatSession.deleted_at.is_(None)).scalar_subquery()
    counts = (await db.execute(select(ready_count(Document), ready_count(YouTubeSource), ready_count(Website), active))).one()
    recent = (select(ChatSession.id, ChatSession.title, ChatSession.updated_at)
              .where(ChatSession.user_id == user.id, ChatSession.deleted_at.is_(None))
              .order_by(ChatSession.updated_at.desc(), ChatSession.id).limit(6).subquery())
    rows = (await db.execute(select(
        recent.c.id, recent.c.title, recent.c.updated_at,
        func.count(Message.id).label("message_count"),
        func.coalesce(func.sum(Message.token_count), 0).label("token_count"),
    ).outerjoin(Message, Message.chat_session_id == recent.c.id)
       .group_by(recent.c.id, recent.c.title, recent.c.updated_at)
       .order_by(recent.c.updated_at.desc(), recent.c.id))).mappings().all()
    return {"stats": dict(zip(["documents", "youtube", "websites", "conversations"], counts)), "recent_sessions": [dict(row) for row in rows]}
