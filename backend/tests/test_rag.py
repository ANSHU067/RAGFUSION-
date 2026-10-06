"""Focused Batch 4 RAG pipeline contract tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.rag.pipelines.rag_pipeline import RAGPipeline


def test_authorized_filter_is_applied_before_top_k():
    pipeline = object.__new__(RAGPipeline)
    pipeline.retriever = MagicMock()
    pipeline.retriever.retrieve.return_value = [
        ("owned", 0.1, {"document_id": "doc-1"})
    ]

    result = RAGPipeline._retrieve_documents(
        pipeline,
        {
            "question": "summarize",
            "metadata": {
                "top_k": 3,
                "authorized_source_ids": {
                    "document": ["doc-1"], "website": [], "youtube": []
                },
            },
        },
    )

    assert result["retrieved_docs"]
    kwargs = pipeline.retriever.retrieve.call_args.kwargs
    assert kwargs["top_k"] == 3
    assert kwargs["filter_dict"] == {
        "$or": [{"document_id": "doc-1"}, {"source_id": "doc-1"}]
    }


def test_history_and_request_generation_settings_reach_llm():
    pipeline = object.__new__(RAGPipeline)
    pipeline.llm = MagicMock()
    pipeline.llm.invoke.return_value = SimpleNamespace(content="answer")

    state = {
        "question": "current",
        "messages": [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "current"},
        ],
        "history": [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ],
        "metadata": {"temperature": 0.0, "max_tokens": 123},
    }

    result = RAGPipeline._generate_response(pipeline, state)

    assert result["response"] == "answer"
    messages = pipeline.llm.invoke.call_args.args[0]
    assert [message.content for message in messages] == [
        "system", "previous question", "previous answer", "current"
    ]
    assert pipeline.llm.invoke.call_args.kwargs == {
        "temperature": 0.0,
        "max_tokens": 123,
    }
