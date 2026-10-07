"""Chat API endpoints."""

import logging
import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_id
from app.db.session import get_db_session
from app.schemas.auth import UserResponse
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionListResponse,
    ChatSessionResponse,
    MessageResponse,
    StreamChunk,
)
from app.services.chat_service import ChatService
from app.services.memory_service import MemoryService
from app.core.exceptions import AppException, NotFoundError
from app.repositories.settings_repository import SettingsRepository
from app.rag.pipelines.rag_pipeline import RAGPipeline
from app.models.entities import Document, Website, YouTubeSource, Embedding, SourceStatus

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sources")
async def list_sources(user=Depends(get_current_user_id), db: AsyncSession = Depends(get_db_session)):
    """List only owned, ready sources with persisted chunks."""
    sources = []
    for kind, model, column, title in (
        ("document", Document, Embedding.document_id, Document.filename),
        ("website", Website, Embedding.website_id, Website.title),
        ("youtube", YouTubeSource, Embedding.youtube_source_id, YouTubeSource.title),
    ):
        rows = await db.execute(select(model.id, title).join(Embedding, column == model.id)
                                .where(model.user_id == user.id, model.status == SourceStatus.ready)
                                .distinct().order_by(title, model.id))
        sources.extend({"id": str(row[0]), "type": kind, "title": row[1] or kind.title()} for row in rows)
    return {"sources": sources}

logger = logging.getLogger(__name__)


async def get_chat_service(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_id),
) -> ChatService:
    """Dependency to get chat service."""
    # Reading chat preferences must not create a row whose schema defaults
    # would mask application defaults for a user with no saved settings.
    settings = await SettingsRepository(db).get_by_user_id(current_user.id)
    pipeline = request.app.state.rag_pipeline
    pipeline_error = getattr(request.app.state, "rag_pipeline_error", None)
    if pipeline is None:
        async with request.app.state.rag_pipeline_lock:
            pipeline = request.app.state.rag_pipeline
            pipeline_error = getattr(request.app.state, "rag_pipeline_error", None)
            if pipeline is None and pipeline_error is None:
                try:
                    pipeline = await asyncio.to_thread(RAGPipeline)
                    request.app.state.rag_pipeline = pipeline
                except Exception as exc:
                    logger.error("RAG pipeline initialization failed", exc_info=True)
                    request.app.state.rag_pipeline_error = exc
                    pipeline_error = exc
    return ChatService(
        db=db,
        user_id=current_user.id,
        rag_pipeline=pipeline,
        model_name=settings.model_name if settings else None,
        provider=settings.provider.value if settings else None,
        configured_temperature=settings.temperature if settings else None,
        configured_max_tokens=settings.max_tokens if settings else None,
        configured_top_k=settings.top_k if settings else None,
        pipeline_error=pipeline_error,
    )


async def get_memory_service(
    db: AsyncSession = Depends(get_db_session),
) -> MemoryService:
    """Dependency to get memory service."""
    return MemoryService(db=db)


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    """Process a chat message with RAG.

    This endpoint:
    - Creates a new session if session_id is null
    - Retrieves relevant documents from the vector store
    - Generates a response using the LLM with context
    - Returns citations and source attribution
    - Persists the conversation

    Args:
        request: Chat request with message and optional session_id

    Returns:
        Chat response with assistant message and sources
    """
    try:
        if request.source_ids is not None:
            await chat_service.select_sources(request.source_ids.model_dump(mode="json"))
        result = await chat_service.chat(
            message=request.message,
            session_id=request.session_id,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_k=request.top_k,
            include_sources=request.include_sources,
        )

        return ChatResponse(
            session_id=result["session_id"],
            message=MessageResponse.model_validate(result["message"]),
            sources=result["sources"],
            token_usage=result["token_usage"],
            processing_time_ms=result["processing_time_ms"],
        )

    except AppException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found") from e
    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat request",
        )


@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    chat_service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """Process a chat message with streaming response.

    This endpoint:
    - Streams the response as it's generated using Server-Sent Events (SSE)
    - Returns chunks of type: content, citation, metadata, done, or error
    - Supports graceful cancellation

    Args:
        request: Chat request with message and optional session_id

    Returns:
        Streaming response with SSE
    """

    if request.source_ids is not None:
        await chat_service.select_sources(request.source_ids.model_dump(mode="json"))
    if request.session_id is not None:
        session = await chat_service.memory_service.get_session(request.session_id, chat_service.user_id)
        if session is None:
            raise NotFoundError("Session", request.session_id)

    async def event_generator():
        """Generate SSE events."""
        try:
            async for chunk in chat_service.chat_stream(
                message=request.message,
                session_id=request.session_id,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_k=request.top_k,
                include_sources=request.include_sources,
            ):
                if await http_request.is_disconnected():
                    return
                chunk_json = chunk.model_dump_json()
                yield f"data: {chunk_json}\n\n"

        except Exception as e:
            logger.error(f"Error in chat stream: {e}", exc_info=True)
            error_chunk = StreamChunk(type="error", error="Unable to process chat stream")
            yield f"data: {error_chunk.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserResponse = Depends(get_current_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
) -> ChatSessionListResponse:
    """List chat sessions for the current user.

    Args:
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip

    Returns:
        List of chat sessions with metadata
    """
    try:
        sessions, total = await memory_service.list_sessions(
            user_id=current_user.id, limit=limit, offset=offset
        )

        message_counts = await memory_service.get_message_counts(
            [session.id for session in sessions]
        )
        session_responses = []
        for session in sessions:
            session_response = ChatSessionResponse.model_validate(session)
            session_response.message_count = message_counts[session.id]
            session_responses.append(session_response)

        return ChatSessionListResponse(sessions=session_responses, total=total)

    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions",
        )


@router.get("/sessions/{session_id}", response_model=ChatHistoryResponse)
async def get_session_history(
    session_id: UUID,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: UserResponse = Depends(get_current_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
) -> ChatHistoryResponse:
    """Get chat session with full message history.

    Args:
        session_id: Session ID

    Returns:
        Chat session with all messages
    """
    try:
        session = await memory_service.get_session(session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        messages = await memory_service.get_messages(session_id, limit=limit, offset=offset)

        message_count = await memory_service.get_message_count(session_id)
        session_response = ChatSessionResponse.model_validate(session)
        session_response.message_count = message_count

        return ChatHistoryResponse(
            session=session_response,
            messages=[MessageResponse.model_validate(msg) for msg in messages],
        )

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session history",
        )


@router.post(
    "/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED
)
async def create_session(
    request: ChatSessionCreate,
    current_user: UserResponse = Depends(get_current_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
) -> ChatSessionResponse:
    """Create a new chat session.

    Args:
        request: Session creation request

    Returns:
        Created chat session
    """
    try:
        session = await memory_service.create_session(
            user_id=current_user.id,
            title=request.title,
            session_metadata=request.session_metadata,
        )

        session_response = ChatSessionResponse.model_validate(session)
        session_response.message_count = 0

        return session_response

    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    current_user: UserResponse = Depends(get_current_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
) -> None:
    """Delete a chat session and all its messages.

    Args:
        session_id: Session ID to delete
    """
    try:
        deleted = await memory_service.delete_session(session_id, current_user.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session",
        )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: UUID,
    request: ChatSessionCreate,
    current_user: UserResponse = Depends(get_current_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
) -> ChatSessionResponse:
    """Update a chat session (title and metadata).

    Args:
        session_id: Session ID
        request: Update request

    Returns:
        Updated chat session
    """
    try:
        session = await memory_service.update_session_title(
            session_id=session_id,
            user_id=current_user.id,
            title=request.title,
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

        message_count = await memory_service.get_message_count(session_id)
        session_response = ChatSessionResponse.model_validate(session)
        session_response.message_count = message_count

        return session_response

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )


@router.delete(
    "/sessions/{session_id}/messages", status_code=status.HTTP_204_NO_CONTENT
)
async def clear_session_messages(
    session_id: UUID,
    current_user: UserResponse = Depends(get_current_user_id),
    memory_service: MemoryService = Depends(get_memory_service),
) -> None:
    """Clear all messages from a chat session.

    Args:
        session_id: Session ID
    """
    try:
        cleared = await memory_service.clear_session_messages(
            session_id, current_user.id
        )
        if not cleared:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
            )

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise
    except Exception as e:
        logger.error(f"Error clearing session messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear session messages",
        )
