"""Embedding manager for document and query embeddings.

This module handles document chunking and embedding generation using
HuggingFace's embedding models.
"""

from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.core.embedding_runtime import SharedEmbeddings
from app.core.rag_config import get_rag_config


class EmbeddingManager:
    """Manages document chunking and embedding generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        """Initialize the embedding manager.

        Args:
            api_key: API key (kept for backwards compatibility if needed)
            model: Embedding model name (defaults to config)
            chunk_size: Size of text chunks (defaults to config)
            chunk_overlap: Overlap between chunks (defaults to config)
        """
        rag_config = get_rag_config()

        self.model = model or rag_config.embedding_model
        self.chunk_size = chunk_size or rag_config.chunk_size
        self.chunk_overlap = chunk_overlap or rag_config.chunk_overlap

        # Initialize embeddings using HuggingFace
        self.embeddings = SharedEmbeddings(self.model)

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

    def chunk_documents(self, documents: List[str]) -> List[str]:
        """Split documents into chunks.

        Args:
            documents: List of document texts

        Returns:
            List of text chunks
        """
        all_chunks = []
        for doc in documents:
            chunks = self.text_splitter.split_text(doc)
            all_chunks.extend(chunks)
        return all_chunks

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a query.

        Args:
            query: Query text

        Returns:
            Embedding vector
        """
        return self.embeddings.embed_query(query)

    def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents.

        Args:
            documents: List of document texts

        Returns:
            List of embedding vectors
        """
        return self.embeddings.embed_documents(documents)

    def embed_and_chunk(
        self, documents: List[str]
    ) -> tuple[List[str], List[List[float]]]:
        """Chunk documents and generate embeddings.

        Args:
            documents: List of document texts

        Returns:
            Tuple of (chunks, embeddings)
        """
        chunks = self.chunk_documents(documents)
        embeddings = self.embed_documents(chunks)
        return chunks, embeddings


if __name__ == "__main__":
    # Example usage
    embedding_manager = EmbeddingManager()

    # Example documents
    docs = [
        "LangChain is a framework for developing applications powered by language models.",
        "RAG (Retrieval Augmented Generation) combines retrieval with generation for better responses.",
    ]

    # Chunk and embed
    chunks, embeddings = embedding_manager.embed_and_chunk(docs)
    print(f"Created {len(chunks)} chunks with {len(embeddings)} embeddings")
    print(f"First chunk: {chunks[0][:100]}...")
    print(f"Embedding dimension: {len(embeddings[0])}")
