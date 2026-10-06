"""Tests for retrieval accuracy metrics.

This module tests retrieval quality using standard IR metrics.
"""
import pytest
from typing import List, Dict, Tuple, Set
import numpy as np
from retrieval import RetrieverManager
from embedding import EmbeddingManager


class RetrievalMetrics:
    """Calculate retrieval accuracy metrics."""

    @staticmethod
    def precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """Calculate Precision@K.

        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            k: Number of top results to consider

        Returns:
            Precision@K score (0-1)
        """
        if k == 0 or len(retrieved_ids) == 0:
            return 0.0

        top_k = retrieved_ids[:k]
        relevant_retrieved = sum(1 for doc_id in top_k if doc_id in relevant_ids)
        return relevant_retrieved / k

    @staticmethod
    def recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """Calculate Recall@K.

        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            k: Number of top results to consider

        Returns:
            Recall@K score (0-1)
        """
        if len(relevant_ids) == 0:
            return 0.0

        top_k = retrieved_ids[:k]
        relevant_retrieved = sum(1 for doc_id in top_k if doc_id in relevant_ids)
        return relevant_retrieved / len(relevant_ids)

    @staticmethod
    def f1_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
        """Calculate F1@K.

        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs
            k: Number of top results to consider

        Returns:
            F1@K score (0-1)
        """
        precision = RetrievalMetrics.precision_at_k(retrieved_ids, relevant_ids, k)
        recall = RetrievalMetrics.recall_at_k(retrieved_ids, relevant_ids, k)

        if precision + recall == 0:
            return 0.0

        return 2 * (precision * recall) / (precision + recall)

    @staticmethod
    def mean_reciprocal_rank(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
        """Calculate Mean Reciprocal Rank (MRR).

        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs

        Returns:
            MRR score (0-1)
        """
        for i, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_ids:
                return 1.0 / i
        return 0.0

    @staticmethod
    def average_precision(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
        """Calculate Average Precision (AP).

        Args:
            retrieved_ids: List of retrieved document IDs
            relevant_ids: Set of relevant document IDs

        Returns:
            AP score (0-1)
        """
        if len(relevant_ids) == 0:
            return 0.0

        precision_sum = 0.0
        relevant_count = 0

        for i, doc_id in enumerate(retrieved_ids, 1):
            if doc_id in relevant_ids:
                relevant_count += 1
                precision_sum += relevant_count / i

        return precision_sum / len(relevant_ids)

    @staticmethod
    def ndcg_at_k(retrieved_ids: List[str], relevance_scores: Dict[str, float], k: int) -> float:
        """Calculate Normalized Discounted Cumulative Gain (NDCG@K).

        Args:
            retrieved_ids: List of retrieved document IDs
            relevance_scores: Dict mapping doc IDs to relevance scores (0-1 or graded)
            k: Number of top results to consider

        Returns:
            NDCG@K score (0-1)
        """
        def dcg(ids: List[str], scores: Dict[str, float], k: int) -> float:
            dcg_sum = 0.0
            for i, doc_id in enumerate(ids[:k], 1):
                rel = scores.get(doc_id, 0.0)
                dcg_sum += (2**rel - 1) / np.log2(i + 1)
            return dcg_sum

        # Calculate DCG
        actual_dcg = dcg(retrieved_ids, relevance_scores, k)

        # Calculate ideal DCG (sort by relevance)
        sorted_ids = sorted(relevance_scores.keys(), key=lambda x: relevance_scores[x], reverse=True)
        ideal_dcg = dcg(sorted_ids, relevance_scores, k)

        if ideal_dcg == 0:
            return 0.0

        return actual_dcg / ideal_dcg


class TestRetrievalAccuracy:
    """Test suite for retrieval accuracy."""

    @pytest.fixture
    def retriever(self):
        """Create a retriever for testing."""
        return RetrieverManager(collection_name="test_retrieval_accuracy")

    @pytest.fixture
    def sample_documents(self):
        """Sample documents with known relevance."""
        return {
            "docs": [
                "Python is a high-level programming language known for its simplicity and readability.",
                "Machine learning is a subset of AI that enables systems to learn from data.",
                "Neural networks are computing systems inspired by biological neural networks.",
                "Deep learning uses multi-layer neural networks for complex pattern recognition.",
                "JavaScript is a programming language commonly used for web development.",
                "Data science combines statistics, programming, and domain expertise.",
                "Natural language processing enables computers to understand human language.",
                "Computer vision allows machines to interpret and understand visual information."
            ],
            "metadata": [
                {"topic": "programming", "language": "python", "id": "doc_0"},
                {"topic": "ai", "subtopic": "ml", "id": "doc_1"},
                {"topic": "ai", "subtopic": "neural_nets", "id": "doc_2"},
                {"topic": "ai", "subtopic": "deep_learning", "id": "doc_3"},
                {"topic": "programming", "language": "javascript", "id": "doc_4"},
                {"topic": "data_science", "id": "doc_5"},
                {"topic": "ai", "subtopic": "nlp", "id": "doc_6"},
                {"topic": "ai", "subtopic": "vision", "id": "doc_7"}
            ],
            "test_cases": [
                {
                    "query": "What is machine learning?",
                    "relevant": {"doc_1", "doc_2", "doc_3"},  # ML, neural nets, deep learning
                    "highly_relevant": {"doc_1"}
                },
                {
                    "query": "Python programming language",
                    "relevant": {"doc_0", "doc_4"},  # Python and JS (both programming)
                    "highly_relevant": {"doc_0"}
                },
                {
                    "query": "Deep neural networks",
                    "relevant": {"doc_2", "doc_3"},  # Neural nets and deep learning
                    "highly_relevant": {"doc_2", "doc_3"}
                }
            ]
        }

    def test_precision_at_k(self, retriever, sample_documents):
        """Test Precision@K metric."""
        # Add documents
        retriever.add_documents(
            sample_documents["docs"],
            sample_documents["metadata"]
        )

        test_case = sample_documents["test_cases"][0]
        query = test_case["query"]
        relevant = test_case["relevant"]

        # Retrieve documents
        results = retriever.retrieve(query, top_k=5)
        retrieved_ids = [meta["id"] for _, _, meta in results]

        # Calculate precision@3
        precision = RetrievalMetrics.precision_at_k(retrieved_ids, relevant, k=3)

        print(f"\nQuery: {query}")
        print(f"Retrieved IDs: {retrieved_ids[:3]}")
        print(f"Relevant IDs: {relevant}")
        print(f"Precision@3: {precision:.3f}")

        # Assert at least some relevant documents are retrieved
        assert precision > 0, "Should retrieve at least one relevant document"

        # Cleanup
        retriever.delete_collection()

    def test_recall_at_k(self, retriever, sample_documents):
        """Test Recall@K metric."""
        retriever.add_documents(
            sample_documents["docs"],
            sample_documents["metadata"]
        )

        test_case = sample_documents["test_cases"][0]
        query = test_case["query"]
        relevant = test_case["relevant"]

        # Retrieve documents
        results = retriever.retrieve(query, top_k=5)
        retrieved_ids = [meta["id"] for _, _, meta in results]

        # Calculate recall@5
        recall = RetrievalMetrics.recall_at_k(retrieved_ids, relevant, k=5)

        print(f"\nQuery: {query}")
        print(f"Recall@5: {recall:.3f}")
        print(f"Relevant found: {sum(1 for id in retrieved_ids[:5] if id in relevant)}/{len(relevant)}")

        assert recall > 0, "Should have non-zero recall"

        retriever.delete_collection()

    def test_mrr(self, retriever, sample_documents):
        """Test Mean Reciprocal Rank."""
        retriever.add_documents(
            sample_documents["docs"],
            sample_documents["metadata"]
        )

        mrr_scores = []

        for test_case in sample_documents["test_cases"]:
            query = test_case["query"]
            relevant = test_case["relevant"]

            results = retriever.retrieve(query, top_k=5)
            retrieved_ids = [meta["id"] for _, _, meta in results]

            mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved_ids, relevant)
            mrr_scores.append(mrr)

            print(f"\nQuery: {query}")
            print(f"Retrieved order: {retrieved_ids}")
            print(f"MRR: {mrr:.3f}")

        avg_mrr = np.mean(mrr_scores)
        print(f"\nAverage MRR: {avg_mrr:.3f}")

        assert avg_mrr > 0, "Should have positive MRR"

        retriever.delete_collection()

    def test_average_precision(self, retriever, sample_documents):
        """Test Average Precision."""
        retriever.add_documents(
            sample_documents["docs"],
            sample_documents["metadata"]
        )

        test_case = sample_documents["test_cases"][0]
        query = test_case["query"]
        relevant = test_case["relevant"]

        results = retriever.retrieve(query, top_k=8)
        retrieved_ids = [meta["id"] for _, _, meta in results]

        ap = RetrievalMetrics.average_precision(retrieved_ids, relevant)

        print(f"\nQuery: {query}")
        print(f"Retrieved: {retrieved_ids}")
        print(f"Relevant: {relevant}")
        print(f"Average Precision: {ap:.3f}")

        assert ap > 0, "Should have positive AP"

        retriever.delete_collection()

    def test_ndcg(self, retriever, sample_documents):
        """Test NDCG@K with graded relevance."""
        retriever.add_documents(
            sample_documents["docs"],
            sample_documents["metadata"]
        )

        test_case = sample_documents["test_cases"][0]
        query = test_case["query"]

        # Define graded relevance (0-2 scale)
        relevance_scores = {
            "doc_1": 2.0,  # Highly relevant (directly answers)
            "doc_2": 1.0,  # Somewhat relevant (related)
            "doc_3": 1.0,  # Somewhat relevant (related)
            "doc_0": 0.0,  # Not relevant
            "doc_4": 0.0,
            "doc_5": 0.5,  # Marginally relevant
            "doc_6": 0.5,
            "doc_7": 0.5
        }

        results = retriever.retrieve(query, top_k=5)
        retrieved_ids = [meta["id"] for _, _, meta in results]

        ndcg = RetrievalMetrics.ndcg_at_k(retrieved_ids, relevance_scores, k=5)

        print(f"\nQuery: {query}")
        print(f"Retrieved order: {retrieved_ids[:5]}")
        print(f"Relevance scores: {[relevance_scores.get(id, 0) for id in retrieved_ids[:5]]}")
        print(f"NDCG@5: {ndcg:.3f}")

        assert 0 <= ndcg <= 1, "NDCG should be between 0 and 1"
        assert ndcg > 0, "Should have positive NDCG"

        retriever.delete_collection()

    def test_multiple_queries_evaluation(self, retriever, sample_documents):
        """Test retrieval across multiple queries."""
        retriever.add_documents(
            sample_documents["docs"],
            sample_documents["metadata"]
        )

        metrics_summary = {
            "precision@3": [],
            "recall@5": [],
            "mrr": [],
            "map": []
        }

        for test_case in sample_documents["test_cases"]:
            query = test_case["query"]
            relevant = test_case["relevant"]

            results = retriever.retrieve(query, top_k=5)
            retrieved_ids = [meta["id"] for _, _, meta in results]

            # Calculate metrics
            p3 = RetrievalMetrics.precision_at_k(retrieved_ids, relevant, k=3)
            r5 = RetrievalMetrics.recall_at_k(retrieved_ids, relevant, k=5)
            mrr = RetrievalMetrics.mean_reciprocal_rank(retrieved_ids, relevant)
            ap = RetrievalMetrics.average_precision(retrieved_ids, relevant)

            metrics_summary["precision@3"].append(p3)
            metrics_summary["recall@5"].append(r5)
            metrics_summary["mrr"].append(mrr)
            metrics_summary["map"].append(ap)

            print(f"\nQuery: {query}")
            print(f"  P@3: {p3:.3f}, R@5: {r5:.3f}, MRR: {mrr:.3f}, AP: {ap:.3f}")

        # Calculate averages
        print("\n" + "="*60)
        print("Average Metrics:")
        for metric, values in metrics_summary.items():
            avg = np.mean(values)
            print(f"  {metric}: {avg:.3f}")

        retriever.delete_collection()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
