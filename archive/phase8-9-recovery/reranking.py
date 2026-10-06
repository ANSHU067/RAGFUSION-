"""Reranking module for the RAG pipeline.

This module improves retrieval quality by reranking documents using cross-encoders.
"""
from typing import List, Tuple, Dict, Optional
from sentence_transformers import CrossEncoder
import numpy as np
from config import RERANK_MODEL, TOP_K_RERANK


class RerankerManager:
    """Manages document reranking using cross-encoder models."""

    def __init__(
        self,
        model_name: str = RERANK_MODEL,
        top_k: int = TOP_K_RERANK
    ):
        """Initialize the reranker.

        Args:
            model_name: Name of the cross-encoder model
            top_k: Number of documents to return after reranking
        """
        self.model_name = model_name
        self.top_k = top_k
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, float, Dict]],
        top_k: Optional[int] = None
    ) -> List[Tuple[str, float, Dict, float]]:
        """Rerank documents using cross-encoder.

        Args:
            query: Query text
            documents: List of tuples (document_text, retrieval_score, metadata)
            top_k: Number of documents to return (defaults to self.top_k)

        Returns:
            List of tuples (document_text, retrieval_score, metadata, rerank_score)
            sorted by rerank_score in descending order
        """
        k = top_k or self.top_k

        if not documents:
            return []

        # Extract document texts
        doc_texts = [doc[0] for doc in documents]

        # Create query-document pairs
        pairs = [[query, doc_text] for doc_text in doc_texts]

        # Get reranking scores
        rerank_scores = self.model.predict(pairs)

        # Combine with original data
        reranked_results = []
        for i, (doc_text, retrieval_score, metadata) in enumerate(documents):
            reranked_results.append((
                doc_text,
                retrieval_score,
                metadata,
                float(rerank_scores[i])
            ))

        # Sort by rerank score (descending)
        reranked_results.sort(key=lambda x: x[3], reverse=True)

        # Return top k
        return reranked_results[:k]

    def rerank_with_scores(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None
    ) -> List[Tuple[str, float]]:
        """Rerank documents and return only text and scores.

        Args:
            query: Query text
            documents: List of document texts
            top_k: Number of documents to return

        Returns:
            List of tuples (document_text, rerank_score)
        """
        k = top_k or self.top_k

        if not documents:
            return []

        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]

        # Get reranking scores
        scores = self.model.predict(pairs)

        # Combine and sort
        results = list(zip(documents, scores))
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:k]

    def get_rerank_scores(
        self,
        query: str,
        documents: List[str]
    ) -> np.ndarray:
        """Get reranking scores for all documents without filtering.

        Args:
            query: Query text
            documents: List of document texts

        Returns:
            Array of reranking scores
        """
        if not documents:
            return np.array([])

        # Create query-document pairs
        pairs = [[query, doc] for doc in documents]

        # Get reranking scores
        scores = self.model.predict(pairs)

        return scores


class HybridReranker:
    """Combines retrieval scores and reranking scores."""

    def __init__(
        self,
        reranker: Optional[RerankerManager] = None,
        retrieval_weight: float = 0.3,
        rerank_weight: float = 0.7
    ):
        """Initialize hybrid reranker.

        Args:
            reranker: RerankerManager instance
            retrieval_weight: Weight for retrieval scores (0-1)
            rerank_weight: Weight for reranking scores (0-1)
        """
        self.reranker = reranker or RerankerManager()
        self.retrieval_weight = retrieval_weight
        self.rerank_weight = rerank_weight

        # Normalize weights
        total = retrieval_weight + rerank_weight
        self.retrieval_weight /= total
        self.rerank_weight /= total

    def hybrid_rerank(
        self,
        query: str,
        documents: List[Tuple[str, float, Dict]],
        top_k: Optional[int] = None
    ) -> List[Tuple[str, float, Dict, float, float]]:
        """Rerank using hybrid scoring.

        Args:
            query: Query text
            documents: List of tuples (document_text, retrieval_score, metadata)
            top_k: Number of documents to return

        Returns:
            List of tuples (document_text, retrieval_score, metadata, rerank_score, hybrid_score)
        """
        k = top_k or self.reranker.top_k

        if not documents:
            return []

        # Get reranking results
        reranked = self.reranker.rerank(query, documents, top_k=len(documents))

        # Normalize scores to 0-1 range
        retrieval_scores = np.array([doc[1] for doc in reranked])
        rerank_scores = np.array([doc[3] for doc in reranked])

        # Min-max normalization
        if retrieval_scores.max() > retrieval_scores.min():
            retrieval_norm = (retrieval_scores - retrieval_scores.min()) / \
                           (retrieval_scores.max() - retrieval_scores.min())
        else:
            retrieval_norm = np.ones_like(retrieval_scores)

        if rerank_scores.max() > rerank_scores.min():
            rerank_norm = (rerank_scores - rerank_scores.min()) / \
                         (rerank_scores.max() - rerank_scores.min())
        else:
            rerank_norm = np.ones_like(rerank_scores)

        # Calculate hybrid scores
        hybrid_scores = (
            self.retrieval_weight * retrieval_norm +
            self.rerank_weight * rerank_norm
        )

        # Combine results
        hybrid_results = []
        for i, (doc_text, retrieval_score, metadata, rerank_score) in enumerate(reranked):
            hybrid_results.append((
                doc_text,
                retrieval_score,
                metadata,
                rerank_score,
                float(hybrid_scores[i])
            ))

        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x[4], reverse=True)

        return hybrid_results[:k]


if __name__ == "__main__":
    # Example usage
    reranker = RerankerManager()

    query = "What is RAG?"
    documents = [
        ("LangChain provides tools for building LLM applications.", 0.85, {"source": "doc1"}),
        ("RAG combines retrieval with generation for better responses.", 0.78, {"source": "doc2"}),
        ("Vector databases enable semantic search.", 0.72, {"source": "doc3"}),
        ("Retrieval Augmented Generation improves accuracy.", 0.80, {"source": "doc4"}),
    ]

    print(f"Query: {query}")
    print(f"\nOriginal ranking (by retrieval score):")
    for i, (text, score, metadata) in enumerate(documents, 1):
        print(f"{i}. [{score:.2f}] {text}")

    # Rerank
    reranked = reranker.rerank(query, documents, top_k=3)

    print(f"\nReranked top 3 (by cross-encoder):")
    for i, (text, ret_score, metadata, rerank_score) in enumerate(reranked, 1):
        print(f"{i}. [Rerank: {rerank_score:.2f}, Retrieval: {ret_score:.2f}] {text}")

    # Hybrid reranking
    print(f"\nHybrid reranking:")
    hybrid_reranker = HybridReranker(reranker)
    hybrid_results = hybrid_reranker.hybrid_rerank(query, documents, top_k=3)

    for i, (text, ret_score, metadata, rerank_score, hybrid_score) in enumerate(hybrid_results, 1):
        print(f"{i}. [Hybrid: {hybrid_score:.2f}, Rerank: {rerank_score:.2f}, Retrieval: {ret_score:.2f}] {text}")
