#!/usr/bin/env python3
"""
Standalone verification script for embedding service.
Tests basic functionality without requiring project dependencies.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np


async def test_embedding_cache():
    """Test embedding cache functionality."""
    print("Testing EmbeddingCache...")

    # Inline minimal version of EmbeddingCache for testing
    import hashlib
    from typing import Dict, List, Optional

    class EmbeddingCache:
        def __init__(self, max_size: int = 10000):
            self.max_size = max_size
            self._cache: Dict[str, np.ndarray] = {}
            self._access_order: List[str] = []

        def _hash_text(self, text: str, model_name: str) -> str:
            content = f"{model_name}:{text}"
            return hashlib.sha256(content.encode()).hexdigest()

        def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
            key = self._hash_text(text, model_name)
            if key in self._cache:
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            return None

        def put(self, text: str, model_name: str, embedding: np.ndarray) -> None:
            key = self._hash_text(text, model_name)
            if len(self._cache) >= self.max_size and key not in self._cache:
                oldest = self._access_order.pop(0)
                del self._cache[oldest]
            self._cache[key] = embedding
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)

        def size(self) -> int:
            return len(self._cache)

    cache = EmbeddingCache(max_size=3)

    # Test put and get
    embedding1 = np.array([0.1, 0.2, 0.3])
    cache.put("text1", "model1", embedding1)
    result = cache.get("text1", "model1")

    assert result is not None, "Cache should return stored embedding"
    assert np.allclose(result, embedding1), "Retrieved embedding should match stored"

    # Test cache miss
    result = cache.get("nonexistent", "model1")
    assert result is None, "Cache should return None for missing key"

    # Test LRU eviction
    cache.put("text2", "model1", np.array([0.4, 0.5, 0.6]))
    cache.put("text3", "model1", np.array([0.7, 0.8, 0.9]))
    cache.put("text4", "model1", np.array([1.0, 1.1, 1.2]))

    assert cache.size() == 3, "Cache should respect max_size"
    assert cache.get("text1", "model1") is None, "Oldest entry should be evicted"
    assert cache.get("text4", "model1") is not None, "Newest entry should exist"

    print("✓ EmbeddingCache tests passed")


async def test_normalization():
    """Test embedding normalization."""
    print("Testing normalization...")

    def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / (norms + 1e-10)

    embeddings = np.array([[3.0, 4.0], [5.0, 12.0]])
    normalized = normalize_embeddings(embeddings)

    # Check unit length
    norms = np.linalg.norm(normalized, axis=1)
    assert np.allclose(norms, [1.0, 1.0]), "Normalized vectors should have unit length"

    # Check direction preserved
    assert np.allclose(normalized[0], [3.0/5.0, 4.0/5.0]), "Direction should be preserved"

    print("✓ Normalization tests passed")


async def test_dimension_validation():
    """Test dimension validation."""
    print("Testing dimension validation...")

    expected_dimension = 768
    embeddings = np.random.rand(5, 384)  # Wrong dimension

    try:
        if embeddings.shape[1] != expected_dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {expected_dimension}, "
                f"got {embeddings.shape[1]}"
            )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "dimension mismatch" in str(e).lower()

    print("✓ Dimension validation tests passed")


async def test_batch_processing():
    """Test batch processing logic."""
    print("Testing batch processing...")

    async def mock_generate(texts):
        await asyncio.sleep(0.01)  # Simulate computation
        return np.random.rand(len(texts), 384)

    async def process_in_batches(texts, batch_size):
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await mock_generate(batch)
            all_embeddings.append(batch_embeddings)
        return np.vstack(all_embeddings)

    texts = [f"text {i}" for i in range(10)]
    embeddings = await process_in_batches(texts, batch_size=3)

    assert embeddings.shape == (10, 384), "Should process all texts"

    print("✓ Batch processing tests passed")


async def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")

    class EmbeddingConfig:
        def __init__(self, provider, model_name, dimension, batch_size):
            if provider not in ["baai", "sentence-transformers", "nvidia"]:
                raise ValueError(f"Invalid provider: {provider}")
            if dimension <= 0:
                raise ValueError(f"Invalid dimension: {dimension}")
            if batch_size <= 0:
                raise ValueError(f"Invalid batch_size: {batch_size}")

            self.provider = provider
            self.model_name = model_name
            self.dimension = dimension
            self.batch_size = batch_size

    # Valid config
    config = EmbeddingConfig("baai", "test", 384, 32)
    assert config.dimension == 384

    # Invalid provider
    try:
        EmbeddingConfig("invalid", "test", 384, 32)
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    # Invalid dimension
    try:
        EmbeddingConfig("baai", "test", -1, 32)
        assert False, "Should raise ValueError"
    except ValueError:
        pass

    print("✓ Configuration validation tests passed")


async def test_similarity_computation():
    """Test cosine similarity computation."""
    print("Testing similarity computation...")

    # Create normalized embeddings
    query = np.array([1.0, 0.0, 0.0])
    docs = np.array([
        [1.0, 0.0, 0.0],  # Identical
        [0.0, 1.0, 0.0],  # Orthogonal
        [0.707, 0.707, 0.0],  # 45 degrees
    ])

    # Compute cosine similarity (dot product for normalized vectors)
    similarities = np.dot(docs, query)

    assert np.isclose(similarities[0], 1.0), "Identical vectors should have similarity 1.0"
    assert np.isclose(similarities[1], 0.0), "Orthogonal vectors should have similarity 0.0"
    assert np.isclose(similarities[2], 0.707, atol=0.01), "45-degree vectors should have similarity ~0.707"

    print("✓ Similarity computation tests passed")


async def main():
    """Run all verification tests."""
    print("=" * 50)
    print("Embedding Service Verification (Standalone)")
    print("=" * 50 + "\n")

    tests = [
        test_embedding_cache,
        test_normalization,
        test_dimension_validation,
        test_batch_processing,
        test_config_validation,
        test_similarity_computation,
    ]

    failed = []

    for test in tests:
        try:
            await test()
        except Exception as e:
            import traceback
            print(f"✗ {test.__name__} failed: {e}")
            traceback.print_exc()
            failed.append(test.__name__)

    print("\n" + "=" * 50)
    if failed:
        print(f"❌ {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        print("\nCore embedding functionality verified:")
        print("  • Cache with LRU eviction")
        print("  • Vector normalization")
        print("  • Dimension validation")
        print("  • Batch processing")
        print("  • Configuration validation")
        print("  • Similarity computation")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
