# YouTube Pipeline for RAG

A comprehensive pipeline for extracting and processing YouTube video content for Retrieval-Augmented Generation (RAG) systems.

## Features

- **Transcript Extraction**: Extract transcripts using `youtube-transcript-api`
- **Metadata Extraction**: Extract video metadata (title, author, duration, views, etc.) using `pytube`
- **Text Chunking**: Split transcripts into manageable chunks with configurable overlap
- **Embedding Generation**: Generate semantic embeddings using sentence-transformers
- **Semantic Search**: Search through video content using natural language queries
- **Batch Processing**: Process multiple videos efficiently
- **Comprehensive Error Handling**: Handles missing transcripts, invalid URLs, and long videos

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Basic Usage

```python
from youtube_pipeline import YouTubePipeline

# Initialize the pipeline
pipeline = YouTubePipeline(
    chunk_size=1000,
    chunk_overlap=200,
    embedding_model="all-MiniLM-L6-v2"
)

# Process a single video
result = pipeline.process("https://www.youtube.com/watch?v=VIDEO_ID")

if result['success']:
    print(f"Processed: {result['metadata']['title']}")
    print(f"Created {len(result['chunks'])} chunks")
    print(f"Processing time: {result['processing_time']:.2f}s")
else:
    print(f"Error: {result['error']}")
```

### Search Through Video Content

```python
# After processing a video with embeddings
chunks = result['chunks']

# Search for relevant content
results = pipeline.search(
    query="What is machine learning?",
    chunks_with_embeddings=chunks,
    top_k=3
)

for i, chunk in enumerate(results, 1):
    print(f"\n{i}. Similarity: {chunk['similarity']:.3f}")
    print(f"   Time: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s")
    print(f"   Text: {chunk['text'][:100]}...")
```

### Batch Processing

```python
# Process multiple videos
video_urls = [
    "https://www.youtube.com/watch?v=VIDEO_ID_1",
    "https://www.youtube.com/watch?v=VIDEO_ID_2",
    "https://www.youtube.com/watch?v=VIDEO_ID_3"
]

results = pipeline.process_batch(
    video_urls,
    continue_on_error=True
)

# Get statistics for each video
for result in results:
    if result['success']:
        stats = pipeline.get_statistics(result)
        print(f"{stats['title']}: {stats['num_chunks']} chunks")
```

## Advanced Usage

### Custom Configuration

```python
from youtube_pipeline import YouTubePipeline

pipeline = YouTubePipeline(
    chunk_size=500,              # Smaller chunks
    chunk_overlap=100,            # Less overlap
    chunk_strategy="sentence",   # Chunk by sentences
    embedding_model="all-mpnet-base-v2",  # Better embeddings
    languages=["en", "es"],      # Prefer English or Spanish
    device="cuda",               # Use GPU for embeddings
    batch_size=64                # Larger batch size
)
```

### Using Individual Components

```python
from youtube_pipeline import (
    TranscriptExtractor,
    MetadataExtractor,
    Chunker,
    EmbeddingGenerator
)

# Extract transcript only
extractor = TranscriptExtractor(languages=["en"])
transcript_result = extractor.extract("VIDEO_URL")

if transcript_result['success']:
    full_text = extractor.get_full_text(transcript_result['transcript'])
    print(full_text)

# Extract metadata only
metadata_extractor = MetadataExtractor()
metadata = metadata_extractor.extract("VIDEO_URL")

if metadata['success']:
    print(f"Title: {metadata['title']}")
    print(f"Duration: {metadata_extractor.format_duration(metadata['length'])}")
    print(f"Views: {metadata['views']:,}")

# Chunk text with different strategies
chunker_fixed = Chunker(chunk_size=1000, strategy="fixed")
chunker_sentence = Chunker(chunk_size=1000, strategy="sentence")
chunker_paragraph = Chunker(chunk_size=1000, strategy="paragraph")

chunks = chunker_sentence.chunk(text)

# Generate embeddings
generator = EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
embedding = generator.generate_single("Sample text")
print(f"Embedding dimension: {len(embedding)}")
```

## Configuration Options

### Chunking Strategies

- **fixed**: Fixed-size chunks with word boundary preservation
- **sentence**: Chunks by complete sentences
- **paragraph**: Chunks by paragraphs

### Embedding Models

Popular sentence-transformer models:

- `all-MiniLM-L6-v2`: Fast, good quality (384 dimensions)
- `all-mpnet-base-v2`: Better quality, slower (768 dimensions)
- `multi-qa-mpnet-base-dot-v1`: Optimized for Q&A tasks

## Error Handling

The pipeline gracefully handles common issues:

- **Missing Transcripts**: Returns error with helpful message
- **Invalid URLs**: Validates and extracts video IDs
- **Long Videos**: Efficiently processes videos of any length
- **Network Issues**: Provides detailed error messages
- **Disabled Transcripts**: Detects and reports when transcripts are disabled

## Testing

Run the test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=youtube_pipeline --cov-report=html

# Run specific test file
pytest tests/test_pipeline.py -v

# Run specific test
pytest tests/test_pipeline.py::TestChunker::test_chunk_long_text -v
```

## Project Structure

```
RAGFUSION/
├── youtube_pipeline/
│   ├── __init__.py
│   ├── pipeline.py              # Main orchestrator
│   ├── transcript_extractor.py  # Transcript extraction
│   ├── metadata_extractor.py    # Metadata extraction
│   ├── chunker.py               # Text chunking
│   └── embedding_generator.py   # Embedding generation
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures
│   └── test_pipeline.py         # Comprehensive tests
├── examples/
│   └── demo.py                  # Usage examples
├── requirements.txt
└── README.md
```

## Performance Tips

1. **GPU Acceleration**: Use `device="cuda"` for faster embedding generation
2. **Batch Processing**: Process multiple videos to amortize model loading time
3. **Chunk Size**: Larger chunks = fewer embeddings but less granular search
4. **Model Selection**: Smaller models are faster but may be less accurate

## Limitations

- Requires videos to have available transcripts (auto-generated or manual)
- Embedding generation can be slow for very long videos (use GPU if available)
- YouTube API rate limits may apply for metadata extraction

## Examples

See `examples/demo.py` for complete working examples including:
- Processing a single video
- Semantic search
- Batch processing
- Error handling
- Statistics and analytics

## License

MIT

## Contributing

Contributions welcome! Please ensure tests pass before submitting PRs.
