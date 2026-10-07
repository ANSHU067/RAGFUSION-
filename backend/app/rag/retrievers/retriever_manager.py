"""Retrieval manager for document storage and retrieval.

This module handles document storage and retrieval using vector similarity search
with ChromaDB.
"""

import logging
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma

from app.core.rag_config import get_rag_config
from app.rag.embeddings.embedding_manager import EmbeddingManager

logger = logging.getLogger(__name__)


class RetrieverManager:
    """Manages document storage and retrieval using ChromaDB."""

    def __init__(
        self,
        collection_name: str = "rag_documents",
        persist_directory: Optional[str] = None,
        embedding_manager: Optional[EmbeddingManager] = None,
        top_k: Optional[int] = None,
    ):
        """Initialize the retriever.

        Args:
            collection_name: Name of the collection in ChromaDB
            persist_directory: Directory to persist the vector store
            embedding_manager: EmbeddingManager instance
            top_k: Number of documents to retrieve
        """
        rag_config = get_rag_config()

        self.collection_name = collection_name
        self.persist_directory = str(persist_directory or rag_config.vector_store_path)
        self.top_k = top_k or rag_config.top_k_retrieval

        # Initialize embedding manager
        self.embedding_manager = embedding_manager or EmbeddingManager()

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory, settings=Settings(
                anonymized_telemetry=False,
                chroma_product_telemetry_impl="app.core.telemetry.DisabledProductTelemetry",
                chroma_telemetry_impl="app.core.telemetry.DisabledProductTelemetry",
            )
        )

        # Initialize vector store
        self.vectorstore = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embedding_manager.embeddings,
        )

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Add documents to the vector store.

        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for each document

        Returns:
            List of document IDs
        """
        # Chunk documents
        chunks = self.embedding_manager.chunk_documents(documents)

        # Prepare metadata and IDs for chunks
        chunk_metadatas = []
        chunk_ids = []

        for i, doc in enumerate(documents):
            doc_chunks = self.embedding_manager.text_splitter.split_text(doc)
            num_chunks = len(doc_chunks)

            for j in range(num_chunks):
                # Create metadata for each chunk
                metadata = (
                    metadatas[i].copy() if metadatas and i < len(metadatas) else {}
                )
                metadata.update(
                    {"source_doc_idx": i, "chunk_idx": j, "total_chunks": num_chunks}
                )
                chunk_metadatas.append(metadata)

                # Create ID for each chunk
                if ids and i < len(ids):
                    chunk_id = f"{ids[i]}_chunk_{j}"
                else:
                    chunk_id = f"doc_{i}_chunk_{j}"
                chunk_ids.append(chunk_id)

        # Add to vector store
        result_ids = self.vectorstore.add_texts(
            texts=chunks, metadatas=chunk_metadatas, ids=chunk_ids
        )

        return result_ids

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_dict: Optional[Dict] = None,
    ) -> List[Tuple[str, float, Dict]]:
        """Retrieve relevant documents for a query.

        Args:
            query: Query text
            top_k: Number of documents to retrieve (defaults to self.top_k)
            filter_dict: Optional metadata filter

        Returns:
            List of tuples (document_text, score, metadata)
        """
        k = top_k or self.top_k

        # Perform similarity search with scores
        if filter_dict:
            results = self.vectorstore.similarity_search_with_score(
                query=query, k=k, filter=filter_dict
            )
        else:
            results = self.vectorstore.similarity_search_with_score(query=query, k=k)

        # Format results
        formatted_results = []
        for index, (doc, score) in enumerate(results):
            metadata = doc.metadata or {}
            content = doc.page_content
            logger.debug(
                "[RAG DEBUG] chunk[%d] type=%s page_content_type=%s "
                "content_length=%d source_type=%s youtube_source_id=%s "
                "source_id=%s metadata_keys=%s",
                index,
                type(doc).__name__,
                type(content).__name__,
                len(content) if isinstance(content, str) else 0,
                metadata.get("source_type"),
                metadata.get("youtube_source_id"),
                metadata.get("source_id"),
                sorted(metadata),
            )
            formatted_results.append((doc.page_content, score, doc.metadata))

        return formatted_results

    @staticmethod
    def document_filter(document_id: str, user_id: str) -> Dict:
        """Scope destructive operations to a document and its owner."""
        return {"$and": [{"document_id": document_id}, {"user_id": user_id}]}

    def get_document_vectors(self, document_id: str, user_id: str) -> Dict:
        return self.client.get_collection(self.collection_name).get(
            where=self.document_filter(document_id, user_id),
            include=["documents", "metadatas", "embeddings"],
        )

    def delete_document_vectors(self, document_id: str, user_id: str) -> None:
        """Delete every matching chunk, including legacy IDs and old tails."""
        self.client.get_collection(self.collection_name).delete(
            where=self.document_filter(document_id, user_id),
        )

    def upsert_vectors(self, records: Dict) -> None:
        """Restore a snapshot in bounded batches without re-embedding."""
        collection = self.client.get_collection(self.collection_name)
        for start in range(0, len(records["ids"]), 100):
            collection.upsert(**{
                key: records[key][start:start + 100]
                for key in ("ids", "documents", "metadatas", "embeddings")
                if records.get(key) is not None
            })

    def add_document_chunks(self, records: Dict) -> None:
        """Index already bounded chunks with the existing Chroma encoder."""
        for start in range(0, len(records["ids"]), 100):
            self.vectorstore.add_texts(
                texts=records["documents"][start:start + 100],
                metadatas=records["metadatas"][start:start + 100],
                ids=records["ids"][start:start + 100],
            )

    def retrieve_with_relevance_scores(
        self, query: str, top_k: Optional[int] = None, score_threshold: float = 0.0
    ) -> List[Tuple[str, float, Dict]]:
        """Retrieve documents with relevance score filtering.

        Args:
            query: Query text
            top_k: Number of documents to retrieve
            score_threshold: Minimum relevance score (0-1, lower is more similar)

        Returns:
            List of tuples (document_text, score, metadata)
        """
        results = self.retrieve(query, top_k)

        # Filter by score threshold
        filtered_results = [
            (text, score, metadata)
            for text, score, metadata in results
            if score <= score_threshold
        ]

        return filtered_results

    def delete_collection(self):
        """Delete the entire collection."""
        self.client.delete_collection(self.collection_name)

    def get_collection_stats(self) -> Dict:
        """Get statistics about the collection.

        Returns:
            Dictionary with collection statistics
        """
        collection = self.client.get_collection(self.collection_name)
        count = collection.count()

        return {
            "name": self.collection_name,
            "count": count,
            "persist_directory": self.persist_directory,
        }


if __name__ == "__main__":
    # Example usage
    retriever = RetrieverManager()

    # Example documents
    docs = [
        "LangChain is a framework for developing applications powered by language models. It provides tools for prompt management, chains, and agents.",
        "RAG (Retrieval Augmented Generation) combines information retrieval with text generation to produce more accurate and grounded responses.",
        "Vector databases store embeddings and enable efficient similarity search for semantic retrieval tasks.",
        "LangGraph extends LangChain with graph-based workflows for building complex multi-agent systems.",
    ]

    # Add documents
    print("Adding documents...")
    ids = retriever.add_documents(
        documents=docs, metadatas=[{"source": f"doc_{i}"} for i in range(len(docs))]
    )
    print(f"Added {len(ids)} document chunks")

    # Retrieve relevant documents
    query = "What is RAG?"
    print(f"\nQuery: {query}")
    results = retriever.retrieve(query, top_k=3)

    print("\nTop 3 results:")
    for i, (text, score, metadata) in enumerate(results, 1):
        print(f"\n{i}. Score: {score:.4f}")
        print(f"   Text: {text[:100]}...")
        print(f"   Metadata: {metadata}")

    # Collection stats
    stats = retriever.get_collection_stats()
    print(f"\nCollection stats: {stats}")
