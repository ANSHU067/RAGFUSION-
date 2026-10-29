"""Process-wide local embedding models shared by ingestion and retrieval."""

from functools import lru_cache, partial
from pathlib import Path
from threading import RLock

import anyio
from langchain_core.embeddings import Embeddings

from app.config.settings import get_settings

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_MODEL_ALIASES = {
    MODEL_NAME.lower(), "all-minilm-l6-v2", "qdrant/all-minilm-l6-v2-onnx",
}
MODEL_LIMITER = anyio.CapacityLimiter(1)
_load_lock = RLock()
_inference_lock = RLock()


@lru_cache(maxsize=1)
def _load_model(model_name: str):
    from fastembed import TextEmbedding

    settings = get_settings()
    cache_dir = Path(settings.embedding_cache_dir).expanduser().resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    return TextEmbedding(
        model_name=model_name,
        cache_dir=str(cache_dir),
        # False by default: a missing cache must trigger a model download.
        local_files_only=settings.embedding_local_files_only,
        threads=1,
        providers=["CPUExecutionProvider"],
        # Release activation buffers instead of retaining an arena at peak size.
        enable_cpu_mem_arena=False,
    )


def get_embedding_model(model_name: str = MODEL_NAME, device: str = "cpu"):
    if device != "cpu":
        raise ValueError("The lightweight embedding runtime requires device='cpu'")
    if model_name.strip().lower() not in _MODEL_ALIASES:
        raise ValueError("Only the shared MiniLM 384-dimensional embedding model is supported")
    # Canonicalize BEFORE the cache lookup so aliases cannot evict/reload the
    # model. Qdrant is the ONNX download repository, not a separate model space.
    # lru_cache alone permits concurrent calls to initialize the same model.
    with _load_lock:
        return _load_model(MODEL_NAME)


def embed_texts(texts: list[str], model_name: str = MODEL_NAME) -> list[list[float]]:
    """Consume the lazy generator in the worker, with bounded inference memory."""
    if not texts:
        return []
    # A sync pipeline and an async ingestion request can run concurrently.
    # Serialize both paths, and never enable FastEmbed multiprocessing.
    with _inference_lock:
        model = get_embedding_model(model_name)
        return [vector.tolist() for vector in model.embed(texts, batch_size=4, parallel=None)]


class SharedEmbeddings(Embeddings):
    """LangChain adapter for the same encoder used by the ingestion service."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return embed_texts(texts, self.model_name)

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await anyio.to_thread.run_sync(
            partial(self.embed_documents, texts), limiter=MODEL_LIMITER
        )

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]
