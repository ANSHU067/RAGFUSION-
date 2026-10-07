"""Phase 3 retrieval, prompt packing, and chat precedence regressions."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.rag.pipelines.rag_pipeline import RAGPipeline
from app.rag.prompts.prompt_builder import PromptBuilder
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService


def _pipeline_with_retrieval(side_effect):
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.side_effect = side_effect
    return pipeline


def test_multisource_retrieval_overfetches_and_backfills_empty_modality():
    document_id = str(uuid4())
    youtube_id = str(uuid4())

    def retrieve(_question, *, top_k, filter_dict):
        if {"document_id": document_id} in filter_dict["$or"]:
            return [
                (f"document {index}", 0.10 + index / 100, {"document_id": document_id, "chunk_index": index})
                for index in range(5)
            ]
        assert {"youtube_source_id": youtube_id} in filter_dict["$or"]
        assert top_k == 10
        return []

    pipeline = _pipeline_with_retrieval(retrieve)
    result = RAGPipeline._retrieve_documents(pipeline, {
        "question": "compare sources",
        "metadata": {
            "top_k": 5,
            "authorized_source_ids": {
                "document": [document_id],
                "website": [],
                "youtube": [youtube_id],
            },
        },
    })

    assert [doc[0] for doc in result["retrieved_docs"]] == [
        "document 0", "document 1", "document 2", "document 3", "document 4",
    ]


def test_multisource_failure_does_not_discard_other_modality():
    document_id = str(uuid4())
    youtube_id = str(uuid4())

    def retrieve(_question, *, filter_dict, **_kwargs):
        if {"document_id": document_id} in filter_dict["$or"]:
            return [("document survives", 0.2, {"document_id": document_id})]
        assert {"youtube_source_id": youtube_id} in filter_dict["$or"]
        raise RuntimeError("YouTube index unavailable")

    pipeline = _pipeline_with_retrieval(retrieve)
    result = RAGPipeline._retrieve_documents(pipeline, {
        "question": "compare sources",
        "metadata": {
            "top_k": 5,
            "authorized_source_ids": {
                "document": [document_id],
                "website": [],
                "youtube": [youtube_id],
            },
        },
    })

    assert [doc[0] for doc in result["retrieved_docs"]] == ["document survives"]
    assert result["metadata"]["retrieval_errors"] == ["youtube"]


def test_prompt_packing_skips_oversized_chunk_and_tracks_exact_ids():
    builder = PromptBuilder(max_context_length=120)
    first_id, second_id = str(uuid4()), str(uuid4())
    documents = [
        ("x" * 500, 0.1, {"chunk_id": first_id, "document_id": str(uuid4()), "filename": "large.txt"}),
        ("small context", 0.2, {"chunk_id": second_id, "document_id": str(uuid4()), "filename": "small.txt"}),
    ]

    packed = builder.pack_context(documents)
    assert packed.chunk_ids == [second_id]
    assert "small context" in packed.text
    assert "large" not in packed.text
    prompt = builder.build_rag_prompt("question", documents, packed_context=packed)
    assert "small context" in prompt
    assert "large" not in prompt


def test_chat_citations_use_only_prompt_context_documents():
    source_id = uuid4()
    service = ChatService(db=None, user_id=uuid4(), rag_pipeline=MagicMock())
    candidates = [
        ("dropped", 0.1, {"source_id": str(uuid4()), "source_type": "document"}),
        ("packed", 0.2, {"source_id": str(source_id), "source_type": "document"}),
    ]
    result = service._convert_citations(service._build_citations([candidates[1]]))
    assert [citation.source_id for citation in result] == [source_id]


def test_chat_request_omitted_generation_parameters_are_none():
    request = ChatRequest(message="hello")
    assert request.temperature is None
    assert request.max_tokens is None
    assert request.top_k is None


def test_chat_service_precedence_request_then_saved_then_application(monkeypatch):
    monkeypatch.setattr("app.services.chat_service.get_rag_config", lambda: SimpleNamespace(
        temperature=0.1, max_tokens=700, top_k_retrieval=11,
    ))
    service = ChatService(
        db=None, user_id=uuid4(), rag_pipeline=object(),
        configured_temperature=0.4, configured_max_tokens=1200, configured_top_k=7,
    )
    values = service._resolve_generation_settings(temperature=None, max_tokens=None, top_k=None)
    assert values == {"temperature": 0.4, "max_tokens": 1200, "top_k": 7}
    values = service._resolve_generation_settings(temperature=0.9, max_tokens=300, top_k=3)
    assert values == {"temperature": 0.9, "max_tokens": 300, "top_k": 3}
