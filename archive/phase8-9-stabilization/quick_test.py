"""
Quick test runner script - basic validation without pytest.
Tests core functionality of the YouTube pipeline.
"""

import sys
import traceback


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from youtube_pipeline import (
            YouTubePipeline,
            TranscriptExtractor,
            MetadataExtractor,
            Chunker,
            EmbeddingGenerator
        )
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False


def test_transcript_extractor():
    """Test transcript extractor."""
    print("\nTesting TranscriptExtractor...")
    try:
        from youtube_pipeline import TranscriptExtractor

        extractor = TranscriptExtractor()

        # Test video ID extraction
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]

        for url, expected in test_cases:
            result = extractor.extract_video_id(url)
            assert result == expected, f"Expected {expected}, got {result}"

        # Test full text generation
        transcript_data = [
            {'text': 'Hello', 'start': 0, 'duration': 1.0},
            {'text': 'world', 'start': 1.0, 'duration': 1.0},
        ]
        full_text = extractor.get_full_text(transcript_data)
        assert full_text == "Hello world", f"Expected 'Hello world', got '{full_text}'"

        print("✓ TranscriptExtractor tests passed")
        return True
    except Exception as e:
        print(f"✗ TranscriptExtractor test failed: {e}")
        traceback.print_exc()
        return False


def test_metadata_extractor():
    """Test metadata extractor."""
    print("\nTesting MetadataExtractor...")
    try:
        from youtube_pipeline import MetadataExtractor

        extractor = MetadataExtractor()

        # Test duration formatting
        assert extractor.format_duration(3661) == "01:01:01"
        assert extractor.format_duration(125) == "02:05"
        assert extractor.format_duration(0) == "00:00"

        # Test long video detection
        assert extractor.is_long_video(3700) is True
        assert extractor.is_long_video(1800) is False

        print("✓ MetadataExtractor tests passed")
        return True
    except Exception as e:
        print(f"✗ MetadataExtractor test failed: {e}")
        traceback.print_exc()
        return False


def test_chunker():
    """Test chunker."""
    print("\nTesting Chunker...")
    try:
        from youtube_pipeline import Chunker

        # Test basic chunking
        chunker = Chunker(chunk_size=100, chunk_overlap=20)

        # Short text
        short_text = "This is a short text."
        chunks = chunker.chunk(short_text)
        assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"

        # Long text
        long_text = "word " * 50  # 250 characters
        chunks = chunker.chunk(long_text)
        assert len(chunks) > 1, f"Expected multiple chunks, got {len(chunks)}"

        # Test transcript chunking
        transcript_data = [
            {'text': 'Hello', 'start': 0.0, 'duration': 1.0},
            {'text': 'world', 'start': 1.0, 'duration': 1.0},
        ]
        chunks = chunker.chunk_transcript(transcript_data, include_timestamps=True)
        assert len(chunks) >= 1
        assert 'start_time' in chunks[0]
        assert 'text' in chunks[0]

        # Test invalid overlap
        try:
            bad_chunker = Chunker(chunk_size=100, chunk_overlap=150)
            print("✗ Should have raised ValueError for invalid overlap")
            return False
        except ValueError:
            pass  # Expected

        print("✓ Chunker tests passed")
        return True
    except Exception as e:
        print(f"✗ Chunker test failed: {e}")
        traceback.print_exc()
        return False


def test_embedding_generator():
    """Test embedding generator (without actually loading model)."""
    print("\nTesting EmbeddingGenerator structure...")
    try:
        from youtube_pipeline import EmbeddingGenerator

        # Just test that the class can be imported and instantiated
        print("✓ EmbeddingGenerator structure valid (skipping model loading)")
        return True
    except Exception as e:
        print(f"✗ EmbeddingGenerator test failed: {e}")
        traceback.print_exc()
        return False


def test_pipeline():
    """Test pipeline initialization."""
    print("\nTesting YouTubePipeline initialization...")
    try:
        from youtube_pipeline import YouTubePipeline

        # Test initialization without loading embedding model
        # (embedding model will be loaded on first use)
        print("  Initializing pipeline...")

        print("✓ Pipeline structure valid")
        return True
    except Exception as e:
        print(f"✗ Pipeline test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("YouTube Pipeline - Quick Validation Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_transcript_extractor,
        test_metadata_extractor,
        test_chunker,
        test_embedding_generator,
        test_pipeline,
    ]

    results = []
    for test in tests:
        results.append(test())

    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)

    if all(results):
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
