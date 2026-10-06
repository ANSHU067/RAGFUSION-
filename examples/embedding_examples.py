"""Example usage of the embedding service."""

import asyncio
import numpy as np
from app.services.embedding_service import get_embedding_service
from app.config.embedding_config import get_embedding_config


async def example_basic_usage():
    """Basic embedding generation example."""
    print("=== Basic Usage ===\n")

    # Get the global embedding service
    service = get_embedding_service()

    # Register a provider
    config = get_embedding_config("all-minilm-l6-v2")
    service.register_provider("default", config)

    # Generate embeddings
    texts = [
        "What is artificial intelligence?",
        "How does machine learning work?",
        "Deep learning explained"
    ]

    embeddings = await service.embed_texts(texts, provider_name="default")
    print(f"Generated {len(embeddings)} embeddings")
    print(f"Shape: {embeddings.shape}")
    print(f"First embedding (truncated): {embeddings[0][:5]}...\n")


async def example_batch_processing():
    """Example of batch processing for large datasets."""
    print("=== Batch Processing ===\n")

    service = get_embedding_service()

    # Register provider with specific batch size
    config = get_embedding_config("bge-small-en-v1.5")
    config.batch_size = 16
    service.register_provider("batch-provider", config)

    # Generate embeddings for many texts
    texts = [f"Document number {i} with some content" for i in range(100)]

    print(f"Processing {len(texts)} texts in batches...")
    embeddings = await service.embed_batch(texts, provider_name="batch-provider")

    print(f"Completed! Shape: {embeddings.shape}\n")


async def example_caching():
    """Example demonstrating caching behavior."""
    print("=== Caching ===\n")

    service = get_embedding_service()

    config = get_embedding_config("all-mpnet-base-v2")
    service.register_provider("cached-provider", config)

    texts = ["Repeated text", "Another text", "Repeated text"]

    # First call
    import time
    start = time.time()
    embeddings1 = await service.embed_texts(texts, provider_name="cached-provider")
    first_time = time.time() - start

    # Second call - should use cache for "Repeated text"
    start = time.time()
    embeddings2 = await service.embed_texts(texts, provider_name="cached-provider")
    second_time = time.time() - start

    print(f"First call: {first_time:.4f}s")
    print(f"Second call: {second_time:.4f}s (with caching)")
    print(f"Speedup: {first_time/second_time:.2f}x\n")

    # Verify embeddings are the same
    np.testing.assert_array_almost_equal(embeddings1, embeddings2)
    print("Embeddings match!\n")


async def example_multiple_providers():
    """Example using multiple embedding providers."""
    print("=== Multiple Providers ===\n")

    service = get_embedding_service()

    # Register multiple providers
    service.register_provider(
        "small-model",
        get_embedding_config("all-minilm-l6-v2")
    )
    service.register_provider(
        "large-model",
        get_embedding_config("bge-large-en-v1.5")
    )

    text = "Sample text for embedding"

    # Get embeddings from different models
    small_emb = await service.embed_text(text, provider_name="small-model")
    large_emb = await service.embed_text(text, provider_name="large-model")

    print(f"Small model dimension: {small_emb.shape[0]}")
    print(f"Large model dimension: {large_emb.shape[0]}\n")


async def example_nvidia_embeddings():
    """Example using NVIDIA NIM API (requires API key)."""
    print("=== NVIDIA Embeddings ===\n")

    import os

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        print("NVIDIA_API_KEY not set, skipping example\n")
        return

    service = get_embedding_service()

    config = get_embedding_config("nvidia-embed-qa")
    service.register_provider("nvidia", config, api_key=api_key)

    texts = ["What is CUDA?", "Explain GPU computing"]

    try:
        embeddings = await service.embed_texts(texts, provider_name="nvidia")
        print(f"Generated embeddings with shape: {embeddings.shape}")
        print(f"Dimension: {embeddings.shape[1]}\n")
    except Exception as e:
        print(f"Error: {e}\n")


async def example_similarity_search():
    """Example of using embeddings for similarity search."""
    print("=== Similarity Search ===\n")

    service = get_embedding_service()

    config = get_embedding_config("all-mpnet-base-v2")
    service.register_provider("search-provider", config)

    # Documents to search
    documents = [
        "Python is a programming language",
        "Machine learning is a subset of AI",
        "The weather is nice today",
        "Deep learning uses neural networks",
        "Java is also a programming language"
    ]

    # Query
    query = "Tell me about artificial intelligence"

    # Generate embeddings
    doc_embeddings = await service.embed_texts(
        documents,
        provider_name="search-provider"
    )
    query_embedding = await service.embed_text(
        query,
        provider_name="search-provider"
    )

    # Compute cosine similarities
    similarities = np.dot(doc_embeddings, query_embedding)

    # Sort by similarity
    ranked_indices = np.argsort(similarities)[::-1]

    print("Query:", query)
    print("\nTop 3 most similar documents:")
    for i, idx in enumerate(ranked_indices[:3], 1):
        print(f"{i}. (score: {similarities[idx]:.4f}) {documents[idx]}")

    print()


async def example_custom_config():
    """Example with custom embedding configuration."""
    print("=== Custom Configuration ===\n")

    from app.services.embedding_service import EmbeddingConfig

    service = get_embedding_service()

    # Create custom config
    custom_config = EmbeddingConfig(
        provider="sentence-transformers",
        model_name="sentence-transformers/paraphrase-MiniLM-L3-v2",
        dimension=384,
        batch_size=64,  # Larger batch size
        max_length=128,  # Shorter max length
        normalize=True,
        cache_enabled=True,
        device="cpu"
    )

    service.register_provider("custom", custom_config)

    texts = ["Custom configuration example"]
    embeddings = await service.embed_texts(texts, provider_name="custom")

    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Config: batch_size={custom_config.batch_size}, "
          f"max_length={custom_config.max_length}\n")


async def main():
    """Run all examples."""
    print("Embedding Service Examples")
    print("=" * 50 + "\n")

    try:
        await example_basic_usage()
        await example_batch_processing()
        await example_caching()
        await example_multiple_providers()
        await example_similarity_search()
        await example_custom_config()
        await example_nvidia_embeddings()

        print("All examples completed successfully!")

    except ImportError as e:
        print(f"\nMissing dependency: {e}")
        print("Install required packages:")
        print("  pip install sentence-transformers")
        print("  pip install FlagEmbedding")
        print("  pip install aiohttp")

    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
