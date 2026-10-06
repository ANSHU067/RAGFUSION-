"""RAG-specific configuration settings.

This module contains configuration for RAG components including:
- Embedding models
- Vector stores
- Retrieval parameters
- Reranking settings
- LLM parameters
"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class RAGConfig(BaseSettings):
    """RAG pipeline configuration."""

    # Model Configuration
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace embedding model",
    )

    llm_model: str = Field(
        default="openai/gpt-oss-120b",
        description="Groq model",
    )

    rerank_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-2-v2",
        description="Cross-encoder model for reranking",
    )

    # Vector Store Configuration
    vector_store_path: Path = Field(
        default_factory=lambda: Path("./data/vectorstore"),
        description="Path to vector store data",
    )

    # Retrieval Configuration
    top_k_retrieval: int = Field(
        default=10,
        description="Number of documents to retrieve initially",
        ge=1,
        le=100,
    )
    top_k_rerank: int = Field(
        default=5, description="Number of documents after reranking", ge=1, le=50
    )

    # Embedding Configuration
    embedding_dimension: int = Field(
        default=384, 
        description="Embedding dimension for all-MiniLM-L6-v2"
    )
    chunk_size: int = Field(
        default=500, description="Size of text chunks", ge=100, le=2000
    )
    chunk_overlap: int = Field(
        default=50, description="Overlap between chunks", ge=0, le=500
    )

    # LLM Configuration
    temperature: float = Field(
        default=0.0, description="LLM temperature", ge=0.0, le=2.0
    )
    max_tokens: int = Field(
        default=1000, description="Maximum tokens for generation", ge=1, le=4000
    )

    # Prompt Configuration
    max_context_length: int = Field(
        default=4000,
        description="Maximum context length in characters",
        ge=1000,
        le=16000,
    )

    # Reranking Configuration
    retrieval_weight: float = Field(
        default=0.3,
        description="Weight for retrieval scores in hybrid reranking",
        ge=0.0,
        le=1.0,
    )
    rerank_weight: float = Field(
        default=0.7,
        description="Weight for reranking scores in hybrid reranking",
        ge=0.0,
        le=1.0,
    )

    # Conversation Memory
    max_conversation_history: int = Field(
        default=5, description="Maximum conversation history to include", ge=0, le=20
    )

    model_config = {
        "env_prefix": "RAG_",
        "case_sensitive": False,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure vector store path exists
        self.vector_store_path.mkdir(parents=True, exist_ok=True)


# Global configuration instance
_rag_config: Optional[RAGConfig] = None


def get_rag_config() -> RAGConfig:
    """Get the global RAG configuration instance.

    Returns:
        RAGConfig instance
    """
    global _rag_config
    if _rag_config is None:
        _rag_config = RAGConfig()
    return _rag_config


def reset_rag_config():
    """Reset the global configuration (useful for testing)."""
    global _rag_config
    _rag_config = None


# For backwards compatibility with old config.py
def get_config_value(key: str, default=None):
    """Get a configuration value by key.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value
    """
    config = get_rag_config()
    return getattr(config, key.lower(), default)


# Convenience accessors for commonly used config values
def EMBEDDING_MODEL():
    return get_rag_config().embedding_model


def LLM_MODEL():
    return get_rag_config().llm_model


def RERANK_MODEL():
    return get_rag_config().rerank_model


def VECTOR_STORE_PATH():
    return get_rag_config().vector_store_path


def TOP_K_RETRIEVAL():
    return get_rag_config().top_k_retrieval


def TOP_K_RERANK():
    return get_rag_config().top_k_rerank


def EMBEDDING_DIMENSION():
    return get_rag_config().embedding_dimension


def CHUNK_SIZE():
    return get_rag_config().chunk_size


def CHUNK_OVERLAP():
    return get_rag_config().chunk_overlap


def TEMPERATURE():
    return get_rag_config().temperature


def MAX_TOKENS():
    return get_rag_config().max_tokens
