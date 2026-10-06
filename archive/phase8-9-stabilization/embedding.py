"""Embedding module for the RAG pipeline.

This module handles document and query embeddings using OpenAI's embedding models.
"""
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)


class EmbeddingManager:
    """Manages document chunking and embedding generation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ):
        """Initialize the embedding manager.

        Args:
            api_key: OpenAI API key (defaults to config)
            model: Embedding model name (defaults to config)
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.api_key = api_key or OPENAI_API_KEY
        self.model = model or EMBEDDING_MODEL

        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env")

        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=self.api_key,
            model=self.model
        )

        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
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

    def embed_and_chunk(self, documents: List[str]) -> tuple[List[str], List[List[float]]]:
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
        "RAG (Retrieval Augmented Generation) combines retrieval with generation for better responses."
    ]

    # Chunk and embed
    chunks, embeddings = embedding_manager.embed_and_chunk(docs)
    print(f"Created {len(chunks)} chunks with {len(embeddings)} embeddings")
    print(f"First chunk: {chunks[0][:100]}...")
    print(f"Embedding dimension: {len(embeddings[0])}")
