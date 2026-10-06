"""Process-wide local embedding models shared by ingestion and retrieval."""

from functools import lru_cache, partial
from threading import RLock

import anyio
from langchain_core.embeddings import Embeddings

from app.config.settings import get_settings

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_LIMITER = anyio.CapacityLimiter(2)
_load_lock = RLock()


@lru_cache(maxsize=8)
def _load_model(model_name: str, device: str):
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(
        model_name,
        device=device,
        cache_folder=settings.embedding_cache_dir,
        local_files_only=settings.embedding_local_files_only,
        trust_remote_code=False,
    )


def get_sentence_transformer(model_name: str = MODEL_NAME, device: str = "cpu"):
    # lru_cache alone permits concurrent calls to initialize the same model.
    with _load_lock:
        return _load_model(model_name, device)


class SharedEmbeddings(Embeddings):
    """LangChain adapter for the same encoder used by the ingestion service."""

    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return get_sentence_transformer(self.model_name).encode(
            texts, batch_size=32, show_progress_bar=False,
            convert_to_numpy=True, normalize_embeddings=False,
        ).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await anyio.to_thread.run_sync(
            partial(self.embed_documents, texts), limiter=MODEL_LIMITER
        )

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]
