"""
YouTube Pipeline for RAG
Extracts transcripts, metadata, chunks, and generates embeddings from YouTube videos.
"""

from .pipeline import YouTubePipeline
from .transcript_extractor import TranscriptExtractor
from .metadata_extractor import MetadataExtractor
from .chunker import Chunker
from .embedding_generator import EmbeddingGenerator

__version__ = "1.0.0"
__all__ = [
    "YouTubePipeline",
    "TranscriptExtractor",
    "MetadataExtractor",
    "Chunker",
    "EmbeddingGenerator",
]
