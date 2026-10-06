"""Consolidated embedding generation helper for all ingestion services."""

from __future__ import annotations

import logging
from typing import Any
from app.config.embedding_config import get_embedding_config
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

_MODEL_ALIASES = {
    "all-minilm-l6-v2": "all-minilm-l6-v2",
    "sentence-transformers/all-MiniLM-L6-v2": "all-minilm-l6-v2",
    # Kept as a compatibility alias for existing persisted settings. The
    # local provider is MiniLM, so callers must use its 384-dimensional space.
    "text-embedding-3-small": "all-minilm-l6-v2",
}


class EmbeddingGenerationError(RuntimeError):
    """Safe public error for embedding failures."""


async def generate_embeddings(
    chunks: list[Any],
    model_name: str,
    dimensions: int | None = None,
) -> list[list[float]]:
    """
    Generate embeddings for text chunks using the embedding service.

    This is a centralized embedding generation function used by all ingestion services.
    Now integrated with embedding_service.py for actual embedding generation.

    Args:
        chunks: List of chunk objects (DocumentChunk, WebsiteChunk, etc.)
        model_name: Embedding model name
        dimensions: Embedding dimensions (default: 1536)

    Returns:
        List of embedding vectors as lists of floats
    """
    if not chunks:
        return []

    try:
        model_key = _MODEL_ALIASES.get(model_name)
        if model_key is None:
            raise ValueError("Unsupported embedding model")
        model_config = get_embedding_config(model_key)
        if dimensions is not None and dimensions != model_config.dimension:
            raise ValueError(
                f"Embedding dimensions must be {model_config.dimension} for this model"
            )

        # Get embedding service (uses singleton from embedding_service.py)
        service = get_embedding_service()
        provider_name = model_key

        # Ensure the provider is registered
        try:
            service.get_provider(provider_name)
        except ValueError:
            service.register_provider(provider_name, model_config)
        
        # Extract text content from chunks
        # Handle both chunk objects with .content attribute and plain strings
        texts = []
        for chunk in chunks:
            if hasattr(chunk, 'content'):
                texts.append(chunk.content)
            elif isinstance(chunk, str):
                texts.append(chunk)
            else:
                texts.append(str(chunk))

        logger.info("Generating %d embeddings with model %s", len(texts), model_config.model_name)

        # Generate embeddings using the embedding service
        # EmbeddingService.embed_texts returns numpy array, convert to list of lists
        embeddings_array = await service.embed_texts(texts, provider_name=provider_name)

        # Convert numpy array to list of lists
        embeddings = embeddings_array.tolist()

        logger.info(f"Successfully generated {len(embeddings)} embeddings, dimension={len(embeddings[0]) if embeddings else 0}")

        return embeddings

    except Exception as exc:
        logger.error("Embedding generation failed", exc_info=True)
        raise EmbeddingGenerationError("Embedding generation failed") from exc
