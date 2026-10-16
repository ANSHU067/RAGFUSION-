"""Regression coverage for the low-memory shared ONNX embedding adapter."""

import asyncio
import sys
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from app.core import embedding_runtime as runtime
from app.config.embedding_config import get_embedding_config
from app.services.embedding_service import FastEmbedProvider


@pytest.fixture
def encoder(monkeypatch):
    calls = []

    class Encoder:
        def __init__(self, **kwargs):
            calls.append(("load", kwargs))

        def embed(self, texts, **kwargs):
            # This executes when consumed, not when the generator is created.
            calls.append(("infer", threading.get_ident(), kwargs))
            for text in texts:
                vector = np.zeros(384, dtype=np.float32)
                vector[len(text) % 384] = 1.0
                yield vector

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=Encoder))
    runtime._load_model.cache_clear()
    yield calls
    runtime._load_model.cache_clear()


@pytest.mark.asyncio
async def test_generator_consumed_in_worker_and_query_document_vectors_match(encoder):
    event_loop_thread = threading.get_ident()
    adapter = runtime.SharedEmbeddings()
    provider = FastEmbedProvider(get_embedding_config("all-minilm-l6-v2"))
    documents, query = await asyncio.gather(
        provider.embed_texts(["same text", "another"]),
        adapter.aembed_query("same text"),
    )
    np.testing.assert_allclose(documents[0], query)
    assert documents.shape == (2, 384)
    assert documents.dtype == np.float32
    loads = [call for call in encoder if call[0] == "load"]
    inferences = [call for call in encoder if call[0] == "infer"]
    assert len(loads) == 1
    assert loads[0][1]["threads"] == 1
    assert loads[0][1]["providers"] == ["CPUExecutionProvider"]
    assert loads[0][1]["enable_cpu_mem_arena"] is False
    assert all(call[1] != event_loop_thread for call in inferences)
    assert all(call[2] == {"batch_size": 4, "parallel": None} for call in inferences)


def test_empty_input_does_not_load_model(encoder):
    assert runtime.SharedEmbeddings().embed_documents([]) == []
    assert encoder == []


def test_document_order_is_preserved(encoder):
    vectors = runtime.SharedEmbeddings().embed_documents(["x", "longer", "x"])
    assert vectors[0] == vectors[2]
    assert vectors[0] != vectors[1]


def test_gpu_request_is_rejected_without_loading(encoder):
    with pytest.raises(ValueError, match="requires device='cpu'"):
        runtime.get_embedding_model(device="cuda")
    assert encoder == []


@pytest.mark.asyncio
async def test_generator_failure_propagates_to_ingestion(monkeypatch):
    class BrokenEncoder:
        def embed(self, *args, **kwargs):
            yield np.zeros(384, dtype=np.float32)
            raise RuntimeError("ONNX inference failed")

    monkeypatch.setattr(runtime, "get_embedding_model", lambda *args: BrokenEncoder())
    provider = FastEmbedProvider(get_embedding_config("all-minilm-l6-v2"))
    with pytest.raises(RuntimeError, match="ONNX inference failed"):
        await provider.embed_texts(["first", "second"])


def test_startup_does_not_import_heavy_optional_components(tmp_path):
    import os
    import subprocess
    from pathlib import Path

    result = subprocess.run(
        [sys.executable, "-c", (
            "import main, sys; "
            "blocked = {'torch', 'torchvision', 'sentence_transformers', "
            "'transformers', 'FlagEmbedding', 'unstructured', 'chromadb'}; "
            "assert not blocked.intersection(sys.modules), blocked.intersection(sys.modules)"
        )],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "RAG_VECTOR_STORE_PATH": str(tmp_path / "vectors")},
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
