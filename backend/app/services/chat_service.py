"""Chat service with RAG integration and streaming support."""

import asyncio
import logging
import time
from typing import Any, AsyncIterator
from uuid import UUID

import anyio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException, NotFoundError
from app.models.entities import (
    Document,
    Embedding,
    MessageRole,
    SourceStatus,
    Website,
    YouTubeSource,
)
from app.rag.pipelines.rag_pipeline import RAGPipeline
from app.schemas.chat import Citation, StreamChunk
from app.services.memory_service import MemoryService
from app.services.youtube_service import ensure_youtube_sources_in_retriever

logger = logging.getLogger(__name__)

_UPLOADED_DOCUMENT_TERMS = ("uploaded document", "uploaded pdf", "uploaded file")
_SOURCE_COUNT_TERMS = (
    "how many sources",
    "number of sources",
    "how many documents",
    "how many videos",
    "how many websites",
)
RAG_LIMITER = anyio.CapacityLimiter(2)


class ChatService:
    """Service for handling chat operations with RAG."""

    def __init__(
        self,
        db: AsyncSession,
        user_id: UUID,
        rag_pipeline: RAGPipeline | None = None,
        max_context_messages: int = 10,
        max_tokens: int = 4000,
        timeout_seconds: int = 60,
        model_name: str | None = None,
        provider: str | None = None,
        configured_temperature: float | None = None,
        configured_max_tokens: int | None = None,
        pipeline_error: Exception | None = None,
    ):
        """Initialize chat service.

        Args:
            db: Database session
            user_id: Current user ID
            rag_pipeline: RAG pipeline instance (will create if None)
            max_context_messages: Maximum messages in context
            max_tokens: Maximum tokens in context
            timeout_seconds: Timeout for LLM responses
        """
        self.db = db
        self.user_id = user_id
        self.rag_pipeline = rag_pipeline
        self.memory_service = MemoryService(
            db=db,
            max_context_messages=max_context_messages,
            max_tokens=max_tokens,
        )
        self.timeout_seconds = timeout_seconds
        self.model_name = model_name
        self.provider = provider
        self.configured_temperature = configured_temperature
        self.configured_max_tokens = configured_max_tokens
        self.pipeline_error = pipeline_error
        self.source_selection: dict[str, list[str]] | None = None

    async def select_sources(self, selection: dict[str, list[str]]) -> None:
        """Validate selections before creating any conversation or message."""
        authorized = await self._get_authorized_source_ids()
        if any(set(values) - set(authorized.get(kind, [])) for kind, values in selection.items()):
            raise NotFoundError("Source", "selected")
        self.source_selection = selection

    def _get_rag_pipeline(self) -> RAGPipeline:
        """Get or create RAG pipeline lazily."""
        if self.pipeline_error is not None:
            raise RuntimeError("RAG pipeline is unavailable") from self.pipeline_error
        if self.rag_pipeline is None:
            # Initialize with default settings
            self.rag_pipeline = RAGPipeline()
        return self.rag_pipeline

    async def chat(
        self,
        message: str,
        session_id: UUID | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_k: int = 5,
        include_sources: bool = True,
    ) -> dict[str, Any]:
        """Process a chat message with RAG.

        Args:
            message: User message
            session_id: Existing session ID or None for new session
            max_tokens: Max tokens for LLM response
            temperature: LLM temperature
            top_k: Number of documents to retrieve
            include_sources: Whether to include source citations

        Returns:
            Dict with session_id, message, sources, token_usage, and processing_time_ms
        """
        start_time = time.time()

        # Get or create session
        if session_id:
            session = await self.memory_service.get_session(session_id, self.user_id)
            if not session:
                raise NotFoundError("Session", session_id)
        else:
            session = await self.memory_service.create_session(
                user_id=self.user_id,
                title=message[:50] + "..." if len(message) > 50 else message,
            )
            session_id = session.id

        # Add user message to history
        await self.memory_service.add_message(
            session_id=session_id,
            role=MessageRole.user,
            content=message,
        )

        # Get conversation context
        context_messages = await self.memory_service.get_context_with_token_limit(
            session_id
        )

        # Build messages for RAG pipeline
        llm_messages = self.memory_service.messages_to_llm_format(context_messages)

        try:
            # Run RAG pipeline with timeout
            response_data = await asyncio.wait_for(
                self._run_rag_pipeline(
                    message=message,
                    history=llm_messages[:-1],  # Exclude the current message
                    session_id=session_id,
                    top_k=top_k,
                    max_tokens=max_tokens if max_tokens is not None else self.configured_max_tokens,
                    temperature=(temperature if temperature is not None else self.configured_temperature),
                ),
                timeout=self.timeout_seconds,
            )

            # Extract response and citations
            response_content = response_data.get("response", "")
            citations_data = response_data.get("citations", [])
            token_usage = response_data.get("token_usage")

            # Add assistant message to history
            assistant_msg = await self.memory_service.add_message(
                session_id=session_id,
                role=MessageRole.assistant,
                content=response_content,
                citations=citations_data if include_sources else [],
                token_count=token_usage.get("total_tokens") if token_usage else None,
            )

            processing_time_ms = (time.time() - start_time) * 1000

            # Convert citations to schema format
            sources = []
            if include_sources:
                sources = self._convert_citations(citations_data)

            return {
                "session_id": session_id,
                "message": assistant_msg,
                "sources": sources,
                "token_usage": token_usage,
                "processing_time_ms": processing_time_ms,
            }

        except asyncio.TimeoutError as exc:
            logger.exception("Chat generation timed out")
            raise AppException("Chat generation timed out", status_code=504) from exc
        except AppException:
            raise
        except SQLAlchemyError:
            raise
        except Exception as exc:
            logger.exception("Chat generation failed")
            raise AppException("Chat generation failed", status_code=502) from exc

    async def chat_stream(
        self,
        message: str,
        session_id: UUID | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_k: int = 5,
        include_sources: bool = True,
    ) -> AsyncIterator[StreamChunk]:
        """Process a chat message with streaming response.

        Args:
            message: User message
            session_id: Existing session ID or None for new session
            max_tokens: Max tokens for LLM response
            temperature: LLM temperature
            top_k: Number of documents to retrieve
            include_sources: Whether to include source citations

        Yields:
            StreamChunk objects
        """
        start_time = time.time()

        try:
            # Get or create session
            if session_id:
                session = await self.memory_service.get_session(
                    session_id, self.user_id
                )
                if not session:
                    yield StreamChunk(
                        type="error", error=f"Session {session_id} not found"
                    )
                    return
            else:
                session = await self.memory_service.create_session(
                    user_id=self.user_id,
                    title=message[:50] + "..." if len(message) > 50 else message,
                )
                session_id = session.id

            # Yield session metadata
            yield StreamChunk(
                type="metadata",
                metadata={"session_id": str(session_id), "status": "started"},
            )

            # Add user message
            await self.memory_service.add_message(
                session_id=session_id,
                role=MessageRole.user,
                content=message,
            )

            # Get conversation context
            context_messages = await self.memory_service.get_context_with_token_limit(
                session_id
            )
            llm_messages = self.memory_service.messages_to_llm_format(context_messages)

            # Stream RAG pipeline response
            response_parts: list[str] = []
            citations_data = []
            token_usage = None

            async with asyncio.timeout(self.timeout_seconds):
                async for chunk in self._run_rag_pipeline_stream(
                    message=message,
                    history=llm_messages[:-1],
                    session_id=session_id,
                    top_k=top_k,
                    max_tokens=max_tokens if max_tokens is not None else self.configured_max_tokens,
                    temperature=(temperature if temperature is not None else self.configured_temperature),
                ):
                    if chunk.get("type") == "content":
                        content = chunk.get("content", "")
                        response_parts.append(content)
                        yield StreamChunk(type="content", content=content)

                    elif chunk.get("type") == "citation":
                        citation_data = chunk.get("citation")
                        if citation_data and include_sources:
                            citations_data.append(citation_data)
                            citation = self._convert_citation(citation_data)
                            yield StreamChunk(type="citation", citation=citation)

                    elif chunk.get("type") == "metadata":
                        token_usage = chunk.get("metadata", {}).get("token_usage")

            # Save assistant message
            await self.memory_service.add_message(
                session_id=session_id,
                role=MessageRole.assistant,
                content="".join(response_parts),
                citations=citations_data if include_sources else [],
                token_count=token_usage.get("total_tokens") if token_usage else None,
            )

            # Yield completion
            processing_time_ms = (time.time() - start_time) * 1000
            yield StreamChunk(
                type="done",
                metadata={
                    "processing_time_ms": processing_time_ms,
                    "token_usage": token_usage,
                },
            )

        except asyncio.TimeoutError:
            logger.error(f"Chat stream timed out after {self.timeout_seconds}s")
            yield StreamChunk(type="error", error="Request timed out")

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Error in chat stream", exc_info=True)
            yield StreamChunk(type="error", error="Chat generation failed")

    async def _run_rag_pipeline(
        self,
        message: str,
        history: list[dict[str, str]],
        session_id: UUID | None = None,
        top_k: int = 5,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Run RAG pipeline to generate response.

        Args:
            message: Current user message
            history: Conversation history
            top_k: Number of documents to retrieve
            max_tokens: Max tokens for response
            temperature: LLM temperature

        Returns:
            Dict with response, citations, and token_usage
        """
        pipeline = self._get_rag_pipeline()

        # Ready videos created before YouTube RAG indexing was added are
        # mirrored into the existing retriever on their owner's first chat.
        await ensure_youtube_sources_in_retriever(self.db, self.user_id)
        authorized_sources = await self._get_authorized_source_ids()
        logger.info(
            "[CHAT RAG DEBUG] user_id=%s chat_session_id=%s "
            "history_message_count=%d retrieved_document_ids=%s "
            "retrieved_youtube_ids=%s retrieved_website_ids=%s "
            "retrieved_chunk_count=pending",
            self.user_id,
            session_id,
            len(history),
            authorized_sources["document"],
            authorized_sources["youtube"],
            authorized_sources["website"],
        )

        # Give a deterministic, truthful answer for the common source-specific
        # request when the user's current database has no uploaded documents.
        # Conversation history remains stored/displayed, but is never evidence
        # that a deleted document still exists.
        if (
            not authorized_sources["document"]
            and any(term in message.lower() for term in _UPLOADED_DOCUMENT_TERMS)
        ):
            logger.info(
                "[CHAT RAG DEBUG] user_id=%s chat_session_id=%s "
                "history_message_count=%d retrieved_document_ids=[] "
                "retrieved_youtube_ids=[] retrieved_website_ids=[] "
                "retrieved_chunk_count=0",
                self.user_id,
                session_id,
                len(history),
            )
            return {
                "response": "There are currently no uploaded documents available to reference.",
                "citations": [],
                "token_usage": None,
            }

        lowered_message = message.casefold()
        if any(term in lowered_message for term in _SOURCE_COUNT_TERMS):
            counts = {
                "documents": len(authorized_sources["document"]),
                "youtube videos": len(authorized_sources["youtube"]),
                "websites": len(authorized_sources["website"]),
            }
            total = sum(counts.values())
            response = (
                f"You have {total} indexed source{'s' if total != 1 else ''}: "
                f"{counts['documents']} document{'s' if counts['documents'] != 1 else ''}, "
                f"{counts['youtube videos']} YouTube video{'s' if counts['youtube videos'] != 1 else ''}, "
                f"and {counts['websites']} website{'s' if counts['websites'] != 1 else ''}."
            )
            return {"response": response, "citations": [], "token_usage": None}

        # Build RAG state
        state = {
            "question": message,
            "history": history,
            "metadata": {
                "top_k": top_k,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "model_name": self.model_name,
                "provider": self.provider,
                "user_id": str(self.user_id),
                # These IDs come from the relational database immediately before
                # retrieval. Chroma is only an index, never proof that a source
                # still exists or belongs to the requesting user.
                "authorized_source_ids": authorized_sources,
                "source_counts": {
                    "document": len(authorized_sources["document"]),
                    "youtube": len(authorized_sources["youtube"]),
                    "website": len(authorized_sources["website"]),
                },
            },
        }

        # Run pipeline
        result = await anyio.to_thread.run_sync(
            pipeline.graph.invoke,
            state,
            limiter=RAG_LIMITER,
            abandon_on_cancel=True,
        )
        retrieval = result.get("metadata", {}).get("retrieval", {})
        logger.info(
            "[CHAT RAG DEBUG] user_id=%s chat_session_id=%s "
            "history_message_count=%d retrieved_document_ids=%s "
            "retrieved_youtube_ids=%s retrieved_website_ids=%s "
            "retrieved_chunk_count=%d",
            self.user_id,
            session_id,
            len(history),
            retrieval.get("document_ids", []),
            retrieval.get("youtube_ids", []),
            retrieval.get("website_ids", []),
            retrieval.get("chunk_count", 0),
        )

        # Extract response
        response = result.get("response", "")

        # Extract citations from reranked docs
        citations = []
        for doc in result.get("reranked_docs", [])[:top_k]:
            content, score, metadata = doc

            normalized_score = max(0.0, min(1.0, 1.0 / (1.0 + float(score))))
            source_type = metadata.get("source_type")
            if source_type not in {"document", "website", "youtube"}:
                source_type = (
                    "youtube" if metadata.get("youtube_source_id")
                    else "website" if metadata.get("website_id")
                    else "document"
                )
            source_id = {
                "document": metadata.get("document_id"),
                "website": metadata.get("website_id"),
                "youtube": metadata.get("youtube_source_id"),
            }.get(source_type) or metadata.get("source_id")
            source_label = (
                metadata.get("title")
                or metadata.get("filename")
                or metadata.get("name")
                or metadata.get("youtube_url")
                or metadata.get("url")
                or "Unknown Source"
            )

            citations.append({
                "source_id": source_id,
                "source_type": source_type,
                "content": content[:200],
                "score": normalized_score,
                "source_name": source_label,
                "filename": source_label,
                "title": metadata.get("title") or (source_label if source_type != "document" else None),
                "url": metadata.get("url") or metadata.get("youtube_url"),
                "metadata": metadata,
            })

        # Extract token usage if available
        token_usage = result.get("metadata", {}).get("token_usage")

        return {
            "response": response,
            "citations": citations,
            "token_usage": token_usage,
        }

    async def _get_authorized_source_ids(self) -> dict[str, list[str]]:
        """Return only ready, owned sources that still have stored chunks.

        This database check deliberately happens for every chat request. It
        prevents deleted/stale vectors from becoming RAG context and provides
        a user-ownership boundary independent of Chroma metadata.
        """
        async def ids_for(model: Any, embedding_column: Any) -> list[str]:
            rows = await self.db.scalars(
                select(model.id)
                .join(Embedding, embedding_column == model.id)
                .where(model.user_id == self.user_id, model.status == SourceStatus.ready)
                .distinct()
            )
            return sorted(str(source_id) for source_id in rows.all())

        authorized = {
            "document": await ids_for(Document, Embedding.document_id),
            "website": await ids_for(Website, Embedding.website_id),
            "youtube": await ids_for(YouTubeSource, Embedding.youtube_source_id),
        }
        if self.source_selection is not None:
            return {kind: sorted(set(ids) & set(self.source_selection.get(kind, [])))
                    for kind, ids in authorized.items()}
        return authorized

    async def _run_rag_pipeline_stream(
        self,
        message: str,
        history: list[dict[str, str]],
        session_id: UUID | None = None,
        top_k: int = 5,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run RAG pipeline with streaming.

        Args:
            message: Current user message
            history: Conversation history
            top_k: Number of documents to retrieve
            max_tokens: Max tokens
            temperature: LLM temperature

        Yields:
            Chunks with type: content, citation, or metadata
        """
        self._get_rag_pipeline()

        # Provider-level streaming is not available in every configured backend.
        # Yield cooperatively without artificial sleeps so this fallback does not
        # add latency or monopolize the event loop for long responses.
        result = await self._run_rag_pipeline(
            message=message,
            history=history,
            session_id=session_id,
            top_k=top_k,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Stream response content in chunks
        response = result.get("response", "")
        chunk_size = 20  # Characters per chunk

        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield {"type": "content", "content": chunk}
            if i and i % (chunk_size * 64) == 0:
                await asyncio.sleep(0)

        # Yield citations
        for citation in result.get("citations", []):
            yield {"type": "citation", "citation": citation}

        # Yield metadata
        yield {
            "type": "metadata",
            "metadata": {"token_usage": result.get("token_usage")},
        }

    def _convert_citation(self, citation_data: dict[str, Any]) -> Citation:
        """Convert citation data to Citation schema.

        Args:
            citation_data: Raw citation data

        Returns:
            Citation schema object
        """
        metadata = citation_data.get("metadata", {})

        source_id = (
            citation_data.get("source_id")
            or metadata.get("source_id")
            or metadata.get("document_id")
            or metadata.get("website_id")
            or metadata.get("youtube_source_id")
        )

        if source_id is None:
            source_id = "00000000-0000-0000-0000-000000000000"

        return Citation(
            source_id=UUID(str(source_id)),
            source_type=citation_data.get("source_type", "document"),
            content=citation_data.get("content", ""),
            score=citation_data.get("score", 0.0),
            source_name=citation_data.get("source_name") or metadata.get("source_name") or metadata.get("title") or metadata.get("filename"),
            title=citation_data.get("title") or metadata.get("title"),
            filename=citation_data.get("filename") or metadata.get("filename"),
            url=citation_data.get("url") or metadata.get("url") or metadata.get("youtube_url"),
            metadata=metadata,
        )

    def _convert_citations(
        self, citations_data: list[dict[str, Any]]
    ) -> list[Citation]:
        """Convert list of citation data to Citation schemas.

        Args:
            citations_data: List of raw citation data

        Returns:
            List of Citation schema objects
        """
        return [self._convert_citation(c) for c in citations_data]
