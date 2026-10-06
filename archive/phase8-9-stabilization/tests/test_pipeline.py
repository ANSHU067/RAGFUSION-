"""
Comprehensive tests for YouTube Pipeline.
Tests missing transcripts, invalid URLs, long videos, and edge cases.
"""

import pytest
from youtube_pipeline import (
    YouTubePipeline,
    TranscriptExtractor,
    MetadataExtractor,
    Chunker,
    EmbeddingGenerator
)


class TestTranscriptExtractor:
    """Tests for transcript extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = TranscriptExtractor()

    def test_extract_video_id_from_standard_url(self):
        """Test extracting video ID from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = self.extractor.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_short_url(self):
        """Test extracting video ID from short YouTube URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = self.extractor.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_embed_url(self):
        """Test extracting video ID from embed URL."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = self.extractor.extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_bare_id(self):
        """Test using bare video ID."""
        video_id = self.extractor.extract_video_id("dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        """Test handling of invalid URL."""
        result = self.extractor.extract("not_a_valid_url")
        assert result['success'] is False
        assert 'Invalid' in result['error']

    def test_invalid_video_id(self):
        """Test handling of invalid video ID."""
        result = self.extractor.extract("invalid_id_123")
        assert result['success'] is False

    def test_missing_transcript(self):
        """Test handling of videos without transcripts."""
        # Use a video ID that typically doesn't have transcripts
        # This is a placeholder - in real testing, you'd use a known video without transcripts
        result = self.extractor.extract("xxxxxxxxxxxxx")
        # Should handle gracefully
        assert 'error' in result
        assert result['success'] is False

    def test_get_full_text(self):
        """Test combining transcript segments into full text."""
        transcript_data = [
            {'text': 'Hello', 'start': 0, 'duration': 1.0},
            {'text': 'world', 'start': 1.0, 'duration': 1.0},
            {'text': '!', 'start': 2.0, 'duration': 0.5}
        ]
        full_text = self.extractor.get_full_text(transcript_data)
        assert full_text == "Hello world !"

    def test_empty_transcript(self):
        """Test handling empty transcript."""
        full_text = self.extractor.get_full_text([])
        assert full_text == ""


class TestMetadataExtractor:
    """Tests for metadata extraction."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = MetadataExtractor()

    def test_format_duration_hours(self):
        """Test duration formatting with hours."""
        formatted = self.extractor.format_duration(3661)
        assert formatted == "01:01:01"

    def test_format_duration_minutes_only(self):
        """Test duration formatting without hours."""
        formatted = self.extractor.format_duration(125)
        assert formatted == "02:05"

    def test_format_duration_zero(self):
        """Test duration formatting for zero."""
        formatted = self.extractor.format_duration(0)
        assert formatted == "00:00"

    def test_is_long_video_true(self):
        """Test long video detection (>1 hour)."""
        assert self.extractor.is_long_video(3700) is True

    def test_is_long_video_false(self):
        """Test long video detection (<1 hour)."""
        assert self.extractor.is_long_video(1800) is False

    def test_is_long_video_custom_threshold(self):
        """Test long video detection with custom threshold."""
        assert self.extractor.is_long_video(600, threshold=500) is True
        assert self.extractor.is_long_video(400, threshold=500) is False

    def test_invalid_url_metadata(self):
        """Test metadata extraction with invalid URL."""
        result = self.extractor.extract("invalid_url")
        assert result['success'] is False
        assert result['error'] is not None


class TestChunker:
    """Tests for text chunking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = Chunker(chunk_size=100, chunk_overlap=20)

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk_size."""
        text = "This is a short text."
        chunks = self.chunker.chunk(text)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_long_text(self):
        """Test chunking long text."""
        text = "word " * 50  # 250 characters
        chunks = self.chunker.chunk(text)
        assert len(chunks) > 1
        # Check overlap exists
        assert any(chunks[i][-10:] in chunks[i+1] for i in range(len(chunks)-1))

    def test_chunk_with_overlap(self):
        """Test that chunks have proper overlap."""
        text = "a" * 200
        chunker = Chunker(chunk_size=100, chunk_overlap=20)
        chunks = chunker.chunk(text)
        assert len(chunks) >= 2

    def test_chunk_sentence_strategy(self):
        """Test sentence-based chunking."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunker = Chunker(chunk_size=30, chunk_overlap=10, strategy="sentence")
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # Each chunk should end with sentence boundary
        for chunk in chunks[:-1]:  # Except possibly last chunk
            assert any(chunk.rstrip().endswith(p) for p in ['.', '!', '?', 'sentence'])

    def test_chunk_paragraph_strategy(self):
        """Test paragraph-based chunking."""
        text = "Para 1 line 1.\nPara 1 line 2.\n\nPara 2 line 1.\nPara 2 line 2."
        chunker = Chunker(chunk_size=100, chunk_overlap=10, strategy="paragraph")
        chunks = chunker.chunk(text)
        assert len(chunks) >= 1

    def test_chunk_transcript_with_timestamps(self):
        """Test chunking transcript with timestamp preservation."""
        transcript_data = [
            {'text': 'Hello', 'start': 0.0, 'duration': 1.0},
            {'text': 'world', 'start': 1.0, 'duration': 1.0},
            {'text': 'this', 'start': 2.0, 'duration': 1.0},
            {'text': 'is', 'start': 3.0, 'duration': 1.0},
            {'text': 'a', 'start': 4.0, 'duration': 1.0},
            {'text': 'test', 'start': 5.0, 'duration': 1.0},
        ]
        chunks = self.chunker.chunk_transcript(transcript_data, include_timestamps=True)

        assert len(chunks) >= 1
        assert all('start_time' in chunk for chunk in chunks)
        assert all('end_time' in chunk for chunk in chunks)
        assert all('segment_indices' in chunk for chunk in chunks)

    def test_chunk_transcript_without_timestamps(self):
        """Test chunking transcript without timestamps."""
        transcript_data = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 2.0},
        ]
        chunks = self.chunker.chunk_transcript(transcript_data, include_timestamps=False)

        assert len(chunks) >= 1
        assert 'start_time' not in chunks[0]

    def test_empty_text_chunking(self):
        """Test chunking empty text."""
        chunks = self.chunker.chunk("")
        assert chunks == []

    def test_invalid_chunk_overlap(self):
        """Test that invalid overlap raises error."""
        with pytest.raises(ValueError):
            Chunker(chunk_size=100, chunk_overlap=150)


class TestEmbeddingGenerator:
    """Tests for embedding generation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use a small model for testing
        self.generator = EmbeddingGenerator(
            model_name="all-MiniLM-L6-v2",
            device="cpu"
        )

    def test_generate_single_embedding(self):
        """Test generating single embedding."""
        text = "This is a test sentence."
        embedding = self.generator.generate_single(text)

        assert embedding is not None
        assert len(embedding) > 0
        assert embedding.shape[0] == self.generator.get_embedding_dimension()

    def test_generate_batch_embeddings(self):
        """Test generating embeddings for multiple chunks."""
        chunks = [
            {'text': 'First chunk of text'},
            {'text': 'Second chunk of text'},
            {'text': 'Third chunk of text'}
        ]

        enriched_chunks = self.generator.generate(chunks, show_progress=False)

        assert len(enriched_chunks) == 3
        assert all('embedding' in chunk for chunk in enriched_chunks)
        assert all('embedding_model' in chunk for chunk in enriched_chunks)
        assert all('embedding_dim' in chunk for chunk in enriched_chunks)

    def test_compute_similarity_cosine(self):
        """Test cosine similarity computation."""
        emb1 = self.generator.generate_single("The cat sat on the mat")
        emb2 = self.generator.generate_single("The cat sat on the mat")
        emb3 = self.generator.generate_single("Python programming language")

        sim_same = self.generator.compute_similarity(emb1, emb2, metric="cosine")
        sim_diff = self.generator.compute_similarity(emb1, emb3, metric="cosine")

        # Same text should have higher similarity
        assert sim_same > sim_diff
        assert 0.99 < sim_same <= 1.0

    def test_search(self):
        """Test semantic search."""
        chunks = [
            {'text': 'Machine learning is a subset of AI'},
            {'text': 'Python is a programming language'},
            {'text': 'Neural networks are used in deep learning'}
        ]

        chunks_with_embeddings = self.generator.generate(chunks, show_progress=False)
        results = self.generator.search(
            "artificial intelligence",
            chunks_with_embeddings,
            top_k=2
        )

        assert len(results) == 2
        assert all('similarity' in r for r in results)
        # ML/AI chunk should be most relevant
        assert 'machine learning' in results[0]['text'].lower() or 'ai' in results[0]['text'].lower()

    def test_empty_chunks(self):
        """Test handling empty chunks."""
        enriched_chunks = self.generator.generate([], show_progress=False)
        assert enriched_chunks == []


class TestYouTubePipeline:
    """Tests for the complete pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = YouTubePipeline(
            chunk_size=100,
            chunk_overlap=20,
            embedding_model="all-MiniLM-L6-v2"
        )

    def test_pipeline_initialization(self):
        """Test pipeline initializes correctly."""
        assert self.pipeline.transcript_extractor is not None
        assert self.pipeline.metadata_extractor is not None
        assert self.pipeline.chunker is not None
        assert self.pipeline.embedding_generator is not None

    def test_get_statistics(self):
        """Test statistics generation."""
        result = {
            'success': True,
            'video_id': 'test123',
            'chunks': [
                {'text': 'test', 'embedding': [0.1, 0.2], 'embedding_dim': 2, 'embedding_model': 'test'}
            ],
            'processing_time': 1.5,
            'metadata': {
                'title': 'Test Video',
                'length': 3700
            },
            'transcript': {
                'language': 'en',
                'transcript': [{'text': 'test'}],
                'auto_generated': False
            }
        }

        stats = self.pipeline.get_statistics(result)

        assert stats['video_id'] == 'test123'
        assert stats['success'] is True
        assert stats['num_chunks'] == 1
        assert stats['title'] == 'Test Video'
        assert stats['is_long_video'] is True
        assert stats['transcript_language'] == 'en'

    def test_invalid_video_pipeline(self):
        """Test pipeline with invalid video."""
        result = self.pipeline.process("invalid_video_id", include_embeddings=False)
        assert result['success'] is False
        assert result['error'] is not None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_very_long_video(self):
        """Test handling of very long videos (>2 hours)."""
        # Create mock long transcript
        long_transcript = [
            {'text': f'Segment {i}', 'start': float(i), 'duration': 1.0}
            for i in range(7200)  # 2 hours worth of 1-second segments
        ]

        chunker = Chunker(chunk_size=1000, chunk_overlap=200)
        chunks = chunker.chunk_transcript(long_transcript)

        # Should handle large transcripts
        assert len(chunks) > 0
        # Should have reasonable number of chunks
        assert len(chunks) < 10000

    def test_unicode_text(self):
        """Test handling of unicode characters."""
        text = "Hello 世界 🌍 Привет مرحبا"
        chunker = Chunker(chunk_size=50, chunk_overlap=10)
        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)

    def test_special_characters(self):
        """Test handling of special characters."""
        text = "Test with special chars: @#$%^&*()[]{}|\\<>?/~`"
        chunker = Chunker(chunk_size=30, chunk_overlap=5)
        chunks = chunker.chunk(text)

        assert len(chunks) > 0

    def test_url_with_parameters(self):
        """Test URL parsing with query parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLtest"
        extractor = TranscriptExtractor()
        video_id = extractor.extract_video_id(url)

        assert video_id == "dQw4w9WgXcQ"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
