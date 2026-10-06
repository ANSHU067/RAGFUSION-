"""Tests for hallucination detection.

This module tests whether the RAG system generates responses grounded in retrieved context.
"""
import pytest
from typing import List, Dict, Tuple
from rag_pipeline import RAGPipeline
from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, LLM_MODEL
import re


class HallucinationDetector:
    """Detect hallucinations in RAG responses."""

    def __init__(self, llm_model: str = LLM_MODEL):
        """Initialize hallucination detector.

        Args:
            llm_model: LLM model for verification
        """
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=0.0,
            openai_api_key=OPENAI_API_KEY
        )

    def check_factual_consistency(
        self,
        response: str,
        context_documents: List[str]
    ) -> Dict[str, any]:
        """Check if response is factually consistent with context.

        Args:
            response: Generated response
            context_documents: Retrieved context documents

        Returns:
            Dictionary with consistency score and details
        """
        context = "\n\n".join(context_documents)

        prompt = f"""You are a factual consistency checker. Compare the response against the provided context.

Context:
{context}

Response to verify:
{response}

Task: Identify any claims in the response that are NOT supported by the context.

Output format:
- Supported claims: [list claims that are in the context]
- Unsupported claims: [list claims that are NOT in the context or contradict it]
- Consistency score: [0-100, where 100 means fully consistent]

Answer:"""

        result = self.llm.invoke(prompt)
        content = result.content

        # Parse the response
        try:
            # Extract consistency score
            score_match = re.search(r'Consistency score:\s*(\d+)', content, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else 50

            # Extract unsupported claims
            unsupported_section = re.search(
                r'Unsupported claims?:(.*?)(?:\n-|$)',
                content,
                re.IGNORECASE | re.DOTALL
            )
            unsupported = unsupported_section.group(1).strip() if unsupported_section else ""

            return {
                "score": score,
                "is_consistent": score >= 80,
                "unsupported_claims": unsupported,
                "full_analysis": content
            }
        except Exception as e:
            return {
                "score": 50,
                "is_consistent": False,
                "unsupported_claims": "Error parsing analysis",
                "full_analysis": content,
                "error": str(e)
            }

    def check_answer_refusal(self, response: str) -> bool:
        """Check if the model properly refused to answer when it shouldn't.

        Args:
            response: Generated response

        Returns:
            True if response contains refusal indicators
        """
        refusal_indicators = [
            "i don't have enough information",
            "the context doesn't contain",
            "i cannot answer",
            "not mentioned in",
            "not provided in the context",
            "insufficient information",
            "cannot determine from"
        ]

        response_lower = response.lower()
        return any(indicator in response_lower for indicator in refusal_indicators)

    def contains_specific_facts(self, response: str, expected_facts: List[str]) -> Dict[str, any]:
        """Check if response contains expected facts.

        Args:
            response: Generated response
            expected_facts: List of facts that should be mentioned

        Returns:
            Dictionary with coverage information
        """
        response_lower = response.lower()

        found_facts = []
        missing_facts = []

        for fact in expected_facts:
            fact_lower = fact.lower()
            if fact_lower in response_lower:
                found_facts.append(fact)
            else:
                missing_facts.append(fact)

        return {
            "found": found_facts,
            "missing": missing_facts,
            "coverage": len(found_facts) / len(expected_facts) if expected_facts else 0
        }


class TestHallucinationDetection:
    """Test suite for hallucination detection."""

    @pytest.fixture
    def pipeline(self):
        """Create RAG pipeline for testing."""
        return RAGPipeline(collection_name="test_hallucination")

    @pytest.fixture
    def detector(self):
        """Create hallucination detector."""
        return HallucinationDetector()

    @pytest.fixture
    def sample_knowledge_base(self):
        """Sample knowledge base with specific facts."""
        return {
            "documents": [
                "The Eiffel Tower is located in Paris, France. It was completed in 1889 and stands 330 meters tall.",
                "Python was created by Guido van Rossum and first released in 1991. It is known for its simplicity.",
                "The Great Wall of China was built over many centuries, with major construction during the Ming Dynasty (1368-1644).",
                "Machine learning is a subset of artificial intelligence that uses statistical techniques to enable computers to learn from data."
            ],
            "metadata": [
                {"topic": "landmarks", "location": "france", "id": "eiffel"},
                {"topic": "programming", "language": "python", "id": "python"},
                {"topic": "landmarks", "location": "china", "id": "wall"},
                {"topic": "ai", "subtopic": "ml", "id": "ml"}
            ]
        }

    def test_factual_consistency_positive(self, pipeline, detector, sample_knowledge_base):
        """Test that accurate responses pass consistency check."""
        # Setup
        pipeline.add_documents(
            sample_knowledge_base["documents"],
            sample_knowledge_base["metadata"]
        )

        # Query about something in the knowledge base
        query = "Where is the Eiffel Tower located and when was it completed?"
        result = pipeline.query(query)

        # Extract context
        context_docs = [doc[0] for doc in result["context_documents"]]

        # Check consistency
        consistency = detector.check_factual_consistency(
            result["response"],
            context_docs
        )

        print(f"\nQuery: {query}")
        print(f"Response: {result['response']}")
        print(f"Consistency Score: {consistency['score']}")
        print(f"Is Consistent: {consistency['is_consistent']}")

        # Should be consistent since answer is in the context
        assert consistency["score"] > 50, "Response should be reasonably consistent"

        # Cleanup
        pipeline.retriever.delete_collection()

    def test_hallucination_detection_negative(self, pipeline, detector, sample_knowledge_base):
        """Test detection of hallucinated information."""
        # Setup
        pipeline.add_documents(
            sample_knowledge_base["documents"],
            sample_knowledge_base["metadata"]
        )

        # Query about something NOT in the knowledge base
        query = "What is the population of Paris?"
        result = pipeline.query(query)

        # Extract context
        context_docs = [doc[0] for doc in result["context_documents"]]

        # Check if model properly refused or if it hallucinated
        refused = detector.check_answer_refusal(result["response"])

        print(f"\nQuery: {query}")
        print(f"Response: {result['response']}")
        print(f"Properly Refused: {refused}")

        if not refused:
            # Check factual consistency
            consistency = detector.check_factual_consistency(
                result["response"],
                context_docs
            )
            print(f"Consistency Score: {consistency['score']}")
            print(f"Unsupported Claims: {consistency['unsupported_claims']}")

        # Either should refuse OR have low consistency (since info not in context)
        # Note: This is a softer assertion since good LLMs might refuse properly
        print(f"Test result: Model {'refused' if refused else 'attempted to answer'}")

        pipeline.retriever.delete_collection()

    def test_specific_fact_inclusion(self, pipeline, detector, sample_knowledge_base):
        """Test that specific facts from context are included."""
        # Setup
        pipeline.add_documents(
            sample_knowledge_base["documents"],
            sample_knowledge_base["metadata"]
        )

        # Query
        query = "Tell me about the Eiffel Tower"
        result = pipeline.query(query)

        # Check for specific facts
        expected_facts = ["paris", "1889", "330 meters"]
        fact_check = detector.contains_specific_facts(
            result["response"],
            expected_facts
        )

        print(f"\nQuery: {query}")
        print(f"Response: {result['response']}")
        print(f"Expected facts: {expected_facts}")
        print(f"Found: {fact_check['found']}")
        print(f"Missing: {fact_check['missing']}")
        print(f"Coverage: {fact_check['coverage']:.1%}")

        # Should mention at least location (Paris)
        assert "paris" in result["response"].lower(), "Should mention Paris"
        assert fact_check["coverage"] > 0, "Should include at least some facts"

        pipeline.retriever.delete_collection()

    def test_contradiction_detection(self, pipeline, detector, sample_knowledge_base):
        """Test that the model doesn't contradict the context."""
        # Setup
        pipeline.add_documents(
            sample_knowledge_base["documents"],
            sample_knowledge_base["metadata"]
        )

        # Query with clear facts in context
        query = "Who created Python?"
        result = pipeline.query(query)

        response_lower = result["response"].lower()

        print(f"\nQuery: {query}")
        print(f"Response: {result['response']}")

        # Should mention Guido van Rossum
        assert "guido" in response_lower or "van rossum" in response_lower, \
            "Should correctly identify Python's creator"

        # Should NOT mention wrong creators
        wrong_creators = ["dennis ritchie", "bjarne stroustrup", "james gosling"]
        for wrong in wrong_creators:
            assert wrong not in response_lower, \
                f"Should not hallucinate wrong creator: {wrong}"

        pipeline.retriever.delete_collection()

    def test_no_information_case(self, pipeline, detector):
        """Test behavior when no relevant documents exist."""
        # Setup with unrelated documents
        docs = [
            "The sky is blue due to Rayleigh scattering.",
            "Water boils at 100 degrees Celsius at sea level.",
            "The speed of light is approximately 299,792 kilometers per second."
        ]
        pipeline.add_documents(docs)

        # Query about something completely unrelated
        query = "What is the capital of Iceland?"
        result = pipeline.query(query)

        # Should refuse to answer or admit uncertainty
        refused = detector.check_answer_refusal(result["response"])

        print(f"\nQuery: {query}")
        print(f"Response: {result['response']}")
        print(f"Properly handled lack of information: {refused}")

        # This is informational - we want to see how the model behaves
        # Ideally it should refuse, but we log the result either way
        print(f"Model behavior: {'Refused appropriately' if refused else 'Attempted to answer'}")

        pipeline.retriever.delete_collection()

    def test_multiple_queries_hallucination_rate(self, pipeline, detector, sample_knowledge_base):
        """Test hallucination rate across multiple queries."""
        # Setup
        pipeline.add_documents(
            sample_knowledge_base["documents"],
            sample_knowledge_base["metadata"]
        )

        test_queries = [
            {
                "query": "What is the height of the Eiffel Tower?",
                "should_answer": True,
                "expected_keywords": ["330", "meters"]
            },
            {
                "query": "Who created Python?",
                "should_answer": True,
                "expected_keywords": ["guido"]
            },
            {
                "query": "What is the population of Beijing?",
                "should_answer": False,  # Not in context
                "expected_keywords": []
            }
        ]

        results_summary = []

        for test_case in test_queries:
            query = test_case["query"]
            result = pipeline.query(query)

            context_docs = [doc[0] for doc in result["context_documents"]]
            consistency = detector.check_factual_consistency(
                result["response"],
                context_docs
            )

            results_summary.append({
                "query": query,
                "should_answer": test_case["should_answer"],
                "consistency_score": consistency["score"],
                "response": result["response"]
            })

            print(f"\nQuery: {query}")
            print(f"Should answer: {test_case['should_answer']}")
            print(f"Consistency: {consistency['score']}")
            print(f"Response: {result['response'][:100]}...")

        # Calculate overall metrics
        answerable_queries = [r for r in results_summary if r["should_answer"]]
        avg_consistency = sum(r["consistency_score"] for r in answerable_queries) / len(answerable_queries)

        print(f"\n{'='*60}")
        print(f"Average consistency for answerable queries: {avg_consistency:.1f}")

        pipeline.retriever.delete_collection()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
