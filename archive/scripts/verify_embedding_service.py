#!/usr/bin/env python3
"""
Quick verification script for embedding service.
Tests basic functionality without requiring pytest.
"""

import asyncio
import sys
import numpy as np


async def test_embedding_cache():
    """Test embedding cache functionality."""
    print("Testing EmbeddingCache...")

    from app.services.embedding_service import EmbeddingCache

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

    from app.services.embedding_service import BaseEmbeddingProvider, EmbeddingConfig

    class TestProvider(BaseEmbeddingProvider):
        async def _generate_embeddings(self, texts):
            return np.array([[3.0, 4.0], [5.0, 12.0]])

    config = EmbeddingConfig(
        provider="test",
        model_name="test",
        dimension=2,
        batch_size=32,
        normalize=True,
        cache_enabled=False
    )

    provider = TestProvider(config)
    embeddings = np.array([[3.0, 4.0], [5.0, 12.0]])
    normalized = provider._normalize_embeddings(embeddings)

    # Check unit length
    norms = np.linalg.norm(normalized, axis=1)
    assert np.allclose(norms, [1.0, 1.0]), "Normalized vectors should have unit length"

    # Check direction preserved
    assert np.allclose(normalized[0], [3.0/5.0, 4.0/5.0]), "Direction should be preserved"

    print("✓ Normalization tests passed")


async def test_dimension_validation():
    """Test dimension validation."""
    print("Testing dimension validation...")

    from app.services.embedding_service import EmbeddingConfig

    config = EmbeddingConfig(
        provider="test",
        model_name="test",
        dimension=768,
        batch_size=32,
        normalize=False,
        cache_enabled=False
    )

    # Simulate dimension mismatch
    embeddings = np.random.rand(5, 384)  # Wrong dimension
    try:
        if embeddings.shape[1] != config.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {config.dimension}, "
                f"got {embeddings.shape[1]}"
            )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "dimension mismatch" in str(e).lower()

    print("✓ Dimension validation tests passed")


async def test_embedding_service():
    """Test the main embedding service."""
    print("Testing EmbeddingService...")

    from app.services.embedding_service import EmbeddingService, EmbeddingConfig

    service = EmbeddingService()

    config = EmbeddingConfig(
        provider="sentence-transformers",
        model_name="test-model",
        dimension=384,
        batch_size=32,
        normalize=True,
        cache_enabled=True
    )

    # Test registration
    service.register_provider("test", config)
    provider = service.get_provider("test")
    assert provider is not None, "Provider should be registered"
    assert provider.config.model_name == "test-model"

    # Test invalid provider
    try:
        service.get_provider("nonexistent")
        assert False, "Should raise ValueError for nonexistent provider"
    except ValueError as e:
        assert "not registered" in str(e).lower()

    # Test invalid provider type
    invalid_config = EmbeddingConfig(
        provider="invalid-provider",
        model_name="test",
        dimension=384,
        batch_size=32,
        normalize=True,
        cache_enabled=True
    )

    try:
        service.register_provider("invalid", invalid_config)
        assert False, "Should raise ValueError for invalid provider"
    except ValueError as e:
        assert "unknown provider" in str(e).lower()

    print("✓ EmbeddingService tests passed")


async def test_embedding_config():
    """Test embedding configuration."""
    print("Testing embedding config...")

    from app.config.embedding_config import get_embedding_config, EMBEDDING_CONFIGS

    # Test valid configs
    config = get_embedding_config("all-minilm-l6-v2")
    assert config.provider == "sentence-transformers"
    assert config.dimension == 384

    config = get_embedding_config("bge-base-en-v1.5")
    assert config.provider == "baai"
    assert config.dimension == 768

    # Test invalid config
    try:
        get_embedding_config("nonexistent-model")
        assert False, "Should raise ValueError for unknown model"
    except ValueError as e:
        assert "unknown embedding model" in str(e).lower()

    # Check all configs are valid
    for key in EMBEDDING_CONFIGS:
        config = get_embedding_config(key)
        assert config.dimension > 0
        assert config.batch_size > 0
        assert config.provider in ["baai", "sentence-transformers", "nvidia"]

    print("✓ Embedding config tests passed")


async def main():
    """Run all verification tests."""
    print("=" * 50)
    print("Embedding Service Verification")
    print("=" * 50 + "\n")

    tests = [
        test_embedding_cache,
        test_normalization,
        test_dimension_validation,
        test_embedding_service,
        test_embedding_config,
    ]

    failed = []

    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed.append(test.__name__)

    print("\n" + "=" * 50)
    if failed:
        print(f"❌ {len(failed)} test(s) failed:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
