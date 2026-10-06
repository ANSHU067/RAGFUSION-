"""Focused regression tests for YouTube RAG indexing and citations."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.entities import Embedding, SourceStatus, YouTubeSource
from app.rag.pipelines.rag_pipeline import RAGPipeline
from app.rag.prompts.prompt_builder import PromptBuilder
from app.services import youtube_service
from app.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_ingestion_mirrors_youtube_chunks_to_rag_retriever(
    test_db, test_user, monkeypatch
):
    """A ready YouTube source must be available to the chat retriever."""

    transcript = "word " * 1_100
    retriever_calls = []

    async def fake_fetch_transcript(video_id, languages):
        return transcript

    async def fake_generate_embeddings(chunks, model_name):
        return [[0.1, 0.2] for _ in chunks]

    class FakeRetriever:
        def add_documents(self, **kwargs):
            retriever_calls.append(kwargs)
            return ["stored"]

    monkeypatch.setattr(youtube_service, "get_session_factory", lambda: test_db)
    monkeypatch.setattr(youtube_service, "fetch_transcript", fake_fetch_transcript)
    monkeypatch.setattr(
        youtube_service, "generate_embeddings", fake_generate_embeddings
    )
    monkeypatch.setattr(youtube_service, "RetrieverManager", FakeRetriever)

    result = await youtube_service.ingest_youtube(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        user_id=test_user.id,
    )

    assert result["status"] == "ready"
    assert len(retriever_calls) == 1
    assert all(
        metadata["source_type"] == "youtube"
        and metadata["youtube_source_id"] == str(result["youtube_source_id"])
        and metadata["user_id"] == str(test_user.id)
        for metadata in retriever_calls[0]["metadatas"]
    )

    async with test_db() as session:
        source = await session.get(YouTubeSource, result["youtube_source_id"])
        embeddings = (
            await session.scalars(
                select(Embedding).where(
                    Embedding.youtube_source_id == result["youtube_source_id"]
                )
            )
        ).all()

    assert source.status == SourceStatus.ready
    assert len(embeddings) == result["total_chunks"]
    assert source.metadata_["rag_indexed"] is True


@pytest.mark.asyncio
async def test_ready_youtube_source_is_backfilled_for_chat(
    test_db, test_user, monkeypatch
):
    """Videos indexed before the mirror existed are made chat-searchable."""

    source = YouTubeSource(
        id=uuid4(),
        user_id=test_user.id,
        video_id="dQw4w9WgXcQ",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        status=SourceStatus.ready,
        metadata_={},
    )
    source_embedding = Embedding(
        youtube_source_id=source.id,
        chunk_index=0,
        content="A transcript chunk available to chat.",
        vector=[0.1, 0.2],
        model_name="test-model",
        metadata_={},
    )
    calls = []

    class FakeRetriever:
        def add_documents(self, **kwargs):
            calls.append(kwargs)
            return ["stored"]

    monkeypatch.setattr(youtube_service, "RetrieverManager", FakeRetriever)

    async with test_db() as session:
        session.add_all([source, source_embedding])
        await session.commit()

        await youtube_service.ensure_youtube_sources_in_retriever(
            session, test_user.id
        )
        await session.refresh(source)

    assert len(calls) == 1
    assert calls[0]["metadatas"][0]["source_type"] == "youtube"
    assert source.metadata_["rag_indexed"] is True


def test_youtube_citation_uses_youtube_source_id():
    """YouTube RAG metadata is converted into a valid API citation."""

    source_id = uuid4()
    service = ChatService(db=SimpleNamespace(), user_id=uuid4())

    citation = service._convert_citation(
        {
            "source_type": "youtube",
            "content": "Transcript excerpt",
            "score": 0.9,
            "metadata": {
                "youtube_source_id": str(source_id),
                "title": "YouTube video (dQw4w9WgXcQ)",
            },
        }
    )

    assert citation.source_id == source_id
    assert citation.source_type == "youtube"


def test_retrieval_excludes_another_users_youtube_chunks():
    """YouTube context is restricted to the authenticated chat user."""

    owner_id = uuid4()
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.return_value = [
        ("owner transcript", 0.2, {"source_type": "youtube", "user_id": str(owner_id)}),
        ("other transcript", 0.1, {"source_type": "youtube", "user_id": str(uuid4())}),
    ]

    result = RAGPipeline._retrieve_documents(
        pipeline,
        {"question": "Summarize the video", "metadata": {"user_id": str(owner_id)}},
    )

    assert [document[0] for document in result["retrieved_docs"]] == [
        "owner transcript"
    ]


def test_video_query_merges_authorized_youtube_results():
    """Video-intent queries search the owner's YouTube subset in Chroma."""

    owner_id = uuid4()
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.side_effect = [
        [("document context", 0.1, {"document_id": str(uuid4())})],
        [
            (
                "YouTube transcript context",
                0.2,
                {
                    "source_type": "youtube",
                    "source_id": str(uuid4()),
                    "youtube_source_id": str(uuid4()),
                    "user_id": str(owner_id),
                    "chunk_index": 0,
                    "chunk_idx": 0,
                },
            )
        ],
    ]

    result = RAGPipeline._retrieve_documents(
        pipeline,
        {
            "question": "Provide a concise summary of the uploaded video.",
            "metadata": {"user_id": str(owner_id)},
        },
    )

    assert [document[0] for document in result["retrieved_docs"]] == [
        "YouTube transcript context",
        "document context",
    ]
    assert pipeline.retriever.retrieve.call_args_list[1].kwargs["filter_dict"] == {
        "$and": [
            {"source_type": "youtube"},
            {"user_id": str(owner_id)},
        ]
    }


def test_youtube_chunks_are_not_dropped_by_an_advisory_distance_threshold():
    """Retrieved YouTube text must reach prompt construction at any distance."""

    owner_id = uuid4()
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.return_value = [
        (
            "The video explains retrieval-augmented generation.",
            1.8,
            {
                "source_type": "youtube",
                "source_id": str(uuid4()),
                "youtube_source_id": str(uuid4()),
                "user_id": str(owner_id),
            },
        )
    ]

    result = RAGPipeline._retrieve_documents(
        pipeline,
        {
            "question": "What is this video about?",
            "metadata": {"user_id": str(owner_id)},
        },
    )

    assert [document[0] for document in result["retrieved_docs"]] == [
        "The video explains retrieval-augmented generation."
    ]
    assert result["metadata"]["rag_context_used"] is True

    pipeline.prompt_builder = PromptBuilder(max_context_length=4_000)
    prompt_state = RAGPipeline._create_prompt(
        pipeline,
        {
            "question": "What is this video about?",
            "reranked_docs": result["retrieved_docs"],
        },
    )

    assert "The video explains retrieval-augmented generation." in prompt_state[
        "messages"
    ][1]["content"]


def test_retrieval_rejects_stale_or_unowned_vectors_when_authorization_is_present():
    """The database authorization set is required before a vector becomes context."""

    owner_id = uuid4()
    live_document_id = uuid4()
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.return_value = [
        ("live chunk", 0.1, {"document_id": str(live_document_id)}),
        ("stale deleted chunk", 0.1, {"document_id": str(uuid4())}),
        ("legacy no source id", 0.1, {"filename": "old.pdf"}),
        (
            "another user's youtube chunk",
            0.1,
            {
                "source_type": "youtube",
                "youtube_source_id": str(uuid4()),
                "user_id": str(owner_id),
            },
        ),
    ]

    result = RAGPipeline._retrieve_documents(
        pipeline,
        {
            "question": "Tell me about the uploaded document",
            "metadata": {
                "user_id": str(owner_id),
                "authorized_source_ids": {
                    "document": [str(live_document_id)],
                    "website": [],
                    "youtube": [],
                },
            },
        },
    )

    assert [document[0] for document in result["retrieved_docs"]] == ["live chunk"]
    assert result["metadata"]["retrieval"] == {
        "chunk_count": 1,
        "document_ids": [str(live_document_id)],
        "website_ids": [],
        "youtube_ids": [],
    }


def test_empty_authorization_set_excludes_every_vector_chunk():
    """A deleted database source cannot be revived by its stale Chroma vector."""

    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.return_value = [
        ("old PDF text", 0.1, {"document_id": str(uuid4()), "filename": "old.pdf"})
    ]

    result = RAGPipeline._retrieve_documents(
        pipeline,
        {
            "question": "Tell me about the uploaded document",
            "metadata": {
                "user_id": str(uuid4()),
                "authorized_source_ids": {"document": [], "website": [], "youtube": []},
            },
        },
    )

    assert result["retrieved_docs"] == []
    assert result["metadata"]["retrieval"]["chunk_count"] == 0
