"""
Demo script showing YouTube Pipeline usage examples.
"""

import json
from youtube_pipeline import YouTubePipeline


def example_1_basic_processing():
    """Example 1: Basic video processing."""
    print("=" * 60)
    print("Example 1: Basic Video Processing")
    print("=" * 60)

    # Initialize pipeline
    pipeline = YouTubePipeline(
        chunk_size=1000,
        chunk_overlap=200,
        embedding_model="all-MiniLM-L6-v2"
    )

    # Process a video (replace with actual YouTube URL)
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    print(f"\nProcessing video: {video_url}")
    result = pipeline.process(video_url)

    if result['success']:
        print("\n✓ Processing successful!")
        print(f"  Video ID: {result['video_id']}")

        if result['metadata']:
            print(f"  Title: {result['metadata']['title']}")
            print(f"  Author: {result['metadata']['author']}")
            print(f"  Duration: {pipeline.metadata_extractor.format_duration(result['metadata']['length'])}")
            print(f"  Views: {result['metadata']['views']:,}")

        print(f"  Transcript language: {result['transcript']['language']}")
        print(f"  Number of chunks: {len(result['chunks'])}")
        print(f"  Processing time: {result['processing_time']:.2f}s")

        # Show first chunk
        if result['chunks']:
            chunk = result['chunks'][0]
            print(f"\n  First chunk preview:")
            print(f"    Time: {chunk.get('start_time', 0):.1f}s - {chunk.get('end_time', 0):.1f}s")
            print(f"    Text: {chunk['text'][:150]}...")
            if 'embedding_dim' in chunk:
                print(f"    Embedding dimension: {chunk['embedding_dim']}")
    else:
        print(f"\n✗ Processing failed: {result['error']}")


def example_2_semantic_search():
    """Example 2: Semantic search through video content."""
    print("\n" + "=" * 60)
    print("Example 2: Semantic Search")
    print("=" * 60)

    pipeline = YouTubePipeline()

    # First process a video
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"\nProcessing video: {video_url}")
    result = pipeline.process(video_url, include_embeddings=True)

    if result['success'] and result['chunks']:
        print(f"✓ Video processed: {len(result['chunks'])} chunks with embeddings")

        # Perform semantic search
        queries = [
            "introduction and overview",
            "main concepts explained",
            "conclusion and summary"
        ]

        for query in queries:
            print(f"\n📝 Query: '{query}'")
            search_results = pipeline.search(
                query=query,
                chunks_with_embeddings=result['chunks'],
                top_k=3
            )

            for i, chunk in enumerate(search_results, 1):
                print(f"\n  {i}. Similarity: {chunk['similarity']:.3f}")
                if 'start_time' in chunk:
                    print(f"     Timestamp: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s")
                print(f"     Text: {chunk['text'][:100]}...")
    else:
        print(f"✗ Could not process video: {result.get('error', 'Unknown error')}")


def example_3_batch_processing():
    """Example 3: Batch processing multiple videos."""
    print("\n" + "=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)

    pipeline = YouTubePipeline(chunk_size=800)

    # List of videos to process
    video_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=9bZkp7q19f0",
        "https://www.youtube.com/watch?v=kJQP7kiw5Fk",
    ]

    print(f"\nProcessing {len(video_urls)} videos...")

    results = pipeline.process_batch(
        video_urls,
        include_embeddings=False,  # Faster without embeddings
        continue_on_error=True
    )

    # Summary
    successful = sum(1 for r in results if r['success'])
    print(f"\n✓ Successfully processed: {successful}/{len(video_urls)} videos")

    # Show statistics for each video
    print("\nVideo Statistics:")
    print("-" * 60)
    for i, result in enumerate(results, 1):
        if result['success']:
            stats = pipeline.get_statistics(result)
            print(f"\n{i}. {stats.get('title', 'Unknown')}")
            print(f"   Duration: {stats.get('duration_formatted', 'N/A')}")
            print(f"   Chunks: {stats['num_chunks']}")
            print(f"   Language: {stats.get('transcript_language', 'N/A')}")
            print(f"   Processing time: {stats['processing_time']:.2f}s")
        else:
            print(f"\n{i}. ✗ Failed: {result.get('error', 'Unknown error')}")


def example_4_individual_components():
    """Example 4: Using individual components."""
    print("\n" + "=" * 60)
    print("Example 4: Using Individual Components")
    print("=" * 60)

    from youtube_pipeline import (
        TranscriptExtractor,
        MetadataExtractor,
        Chunker,
        EmbeddingGenerator
    )

    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # 1. Extract transcript
    print("\n1. Extracting transcript...")
    transcript_extractor = TranscriptExtractor(languages=["en"])
    transcript_result = transcript_extractor.extract(video_url)

    if transcript_result['success']:
        print(f"   ✓ Transcript extracted ({len(transcript_result['transcript'])} segments)")
        full_text = transcript_extractor.get_full_text(transcript_result['transcript'])
        print(f"   Total characters: {len(full_text)}")
    else:
        print(f"   ✗ Failed: {transcript_result['error']}")
        return

    # 2. Extract metadata
    print("\n2. Extracting metadata...")
    metadata_extractor = MetadataExtractor()
    metadata_result = metadata_extractor.extract(video_url)

    if metadata_result['success']:
        print(f"   ✓ Title: {metadata_result['title']}")
        print(f"   Author: {metadata_result['author']}")
        print(f"   Duration: {metadata_extractor.format_duration(metadata_result['length'])}")
        print(f"   Is long video: {metadata_extractor.is_long_video(metadata_result['length'])}")
    else:
        print(f"   ✗ Failed: {metadata_result['error']}")

    # 3. Chunk the text
    print("\n3. Chunking text...")
    chunker = Chunker(chunk_size=500, chunk_overlap=100, strategy="sentence")
    chunks = chunker.chunk_transcript(transcript_result['transcript'])
    print(f"   ✓ Created {len(chunks)} chunks")
    print(f"   First chunk: {chunks[0]['text'][:80]}...")

    # 4. Generate embeddings
    print("\n4. Generating embeddings...")
    generator = EmbeddingGenerator(model_name="all-MiniLM-L6-v2", device="cpu")
    chunks_with_embeddings = generator.generate(chunks[:5], show_progress=False)  # Just first 5
    print(f"   ✓ Generated {len(chunks_with_embeddings)} embeddings")
    print(f"   Embedding dimension: {generator.get_embedding_dimension()}")


def example_5_error_handling():
    """Example 5: Demonstrating error handling."""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)

    pipeline = YouTubePipeline()

    test_cases = [
        ("Invalid URL", "not_a_valid_url"),
        ("Invalid video ID", "xxxxxxxxxxxxx"),
        ("Non-existent video", "https://www.youtube.com/watch?v=nonexistent12"),
    ]

    for name, test_url in test_cases:
        print(f"\n{name}: {test_url}")
        result = pipeline.process(test_url, include_embeddings=False)

        if result['success']:
            print(f"   ✓ Unexpectedly succeeded")
        else:
            print(f"   ✗ Failed as expected: {result['error']}")


def example_6_chunking_strategies():
    """Example 6: Comparing different chunking strategies."""
    print("\n" + "=" * 60)
    print("Example 6: Chunking Strategies Comparison")
    print("=" * 60)

    from youtube_pipeline import Chunker

    # Sample text
    text = """
    Machine learning is a subset of artificial intelligence. It focuses on training algorithms.
    These algorithms can make predictions based on data. There are three main types of machine learning.

    First, supervised learning uses labeled data. Second, unsupervised learning finds patterns.
    Third, reinforcement learning learns through trial and error.

    Each type has its own use cases and applications. The choice depends on your problem.
    """

    strategies = ["fixed", "sentence", "paragraph"]

    for strategy in strategies:
        chunker = Chunker(chunk_size=100, chunk_overlap=20, strategy=strategy)
        chunks = chunker.chunk(text)

        print(f"\n{strategy.upper()} strategy:")
        print(f"  Number of chunks: {len(chunks)}")
        print(f"  First chunk: {chunks[0][:80]}...")
        if len(chunks) > 1:
            print(f"  Last chunk: {chunks[-1][:80]}...")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("YouTube Pipeline - Demo Examples")
    print("=" * 60)
    print("\nNote: Some examples use placeholder URLs that may not work.")
    print("Replace with actual YouTube URLs for real testing.")

    try:
        # Uncomment the examples you want to run
        example_1_basic_processing()
        # example_2_semantic_search()
        # example_3_batch_processing()
        # example_4_individual_components()
        # example_5_error_handling()
        # example_6_chunking_strategies()

        print("\n" + "=" * 60)
        print("Demo completed!")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError during demo: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
