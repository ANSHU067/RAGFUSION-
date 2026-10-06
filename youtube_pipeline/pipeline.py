"""
Main YouTube Pipeline orchestrator.
Coordinates transcript extraction, metadata extraction, chunking, and embedding generation.
"""

from typing import Dict, List, Optional
import logging
from datetime import datetime

from .transcript_extractor import TranscriptExtractor
from .metadata_extractor import MetadataExtractor
from .chunker import Chunker
from .embedding_generator import EmbeddingGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YouTubePipeline:
    """
    Main pipeline for processing YouTube videos.
    Extracts transcripts, metadata, chunks text, and generates embeddings.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        chunk_strategy: str = "fixed",
        embedding_model: str = "all-MiniLM-L6-v2",
        languages: List[str] = None,
        device: Optional[str] = None,
        batch_size: int = 32
    ):
        """
        Initialize the YouTube pipeline.

        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between chunks
            chunk_strategy: Chunking strategy ('fixed', 'sentence', 'paragraph')
            embedding_model: Sentence-transformer model name
            languages: Preferred transcript languages
            device: Device for embeddings ('cuda', 'cpu', or None)
            batch_size: Batch size for embedding generation
        """
        self.transcript_extractor = TranscriptExtractor(languages=languages)
        self.metadata_extractor = MetadataExtractor()
        self.chunker = Chunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            strategy=chunk_strategy
        )
        self.embedding_generator = EmbeddingGenerator(
            model_name=embedding_model,
            device=device,
            batch_size=batch_size
        )

        logger.info("YouTube Pipeline initialized")

    def process(
        self,
        video_url: str,
        include_metadata: bool = True,
        include_embeddings: bool = True,
        include_timestamps: bool = True
    ) -> Dict:
        """
        Process a YouTube video through the complete pipeline.

        Args:
            video_url: YouTube URL or video ID
            include_metadata: Whether to extract metadata
            include_embeddings: Whether to generate embeddings
            include_timestamps: Whether to include timestamp info in chunks

        Returns:
            Dictionary containing all extracted data:
                - success: bool
                - video_id: str
                - metadata: Dict (if include_metadata=True)
                - transcript: Dict
                - chunks: List[Dict]
                - processing_time: float
                - error: str (if failed)
        """
        start_time = datetime.now()

        result = {
            'success': False,
            'video_id': None,
            'metadata': None,
            'transcript': None,
            'chunks': None,
            'processing_time': None,
            'error': None
        }

        try:
            logger.info(f"Processing video: {video_url}")

            # Step 1: Extract transcript
            logger.info("Step 1: Extracting transcript...")
            transcript_result = self.transcript_extractor.extract(video_url)

            if not transcript_result['success']:
                result['error'] = transcript_result['error']
                result['video_id'] = transcript_result['video_id']
                return result

            result['video_id'] = transcript_result['video_id']
            result['transcript'] = transcript_result

            # Step 2: Extract metadata (optional)
            if include_metadata:
                logger.info("Step 2: Extracting metadata...")
                metadata_result = self.metadata_extractor.extract(video_url)

                if metadata_result['success']:
                    result['metadata'] = metadata_result
                    logger.info(f"Metadata extracted: {metadata_result['title']}")
                else:
                    logger.warning(f"Metadata extraction failed: {metadata_result['error']}")
                    # Continue processing even if metadata fails

            # Step 3: Chunk transcript
            logger.info("Step 3: Chunking transcript...")
            chunks = self.chunker.chunk_transcript(
                transcript_result['transcript'],
                include_timestamps=include_timestamps
            )
            logger.info(f"Created {len(chunks)} chunks")
            result['chunks'] = chunks

            # Step 4: Generate embeddings (optional)
            if include_embeddings:
                logger.info("Step 4: Generating embeddings...")
                chunks_with_embeddings = self.embedding_generator.generate(
                    chunks,
                    show_progress=True
                )
                result['chunks'] = chunks_with_embeddings
                logger.info(f"Generated embeddings for {len(chunks_with_embeddings)} chunks")

            # Success!
            result['success'] = True
            processing_time = (datetime.now() - start_time).total_seconds()
            result['processing_time'] = processing_time

            logger.info(f"Pipeline completed successfully in {processing_time:.2f}s")
            return result

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            result['error'] = f"Pipeline error: {str(e)}"
            return result

    def process_batch(
        self,
        video_urls: List[str],
        include_metadata: bool = True,
        include_embeddings: bool = True,
        include_timestamps: bool = True,
        continue_on_error: bool = True
    ) -> List[Dict]:
        """
        Process multiple YouTube videos.

        Args:
            video_urls: List of YouTube URLs or video IDs
            include_metadata: Whether to extract metadata
            include_embeddings: Whether to generate embeddings
            include_timestamps: Whether to include timestamp info
            continue_on_error: Whether to continue if one video fails

        Returns:
            List of results for each video
        """
        results = []

        logger.info(f"Processing batch of {len(video_urls)} videos")

        for idx, video_url in enumerate(video_urls, 1):
            logger.info(f"Processing video {idx}/{len(video_urls)}")

            try:
                result = self.process(
                    video_url,
                    include_metadata=include_metadata,
                    include_embeddings=include_embeddings,
                    include_timestamps=include_timestamps
                )
                results.append(result)

                if not result['success'] and not continue_on_error:
                    logger.error("Stopping batch processing due to error")
                    break

            except Exception as e:
                logger.error(f"Error processing video {video_url}: {str(e)}")
                results.append({
                    'success': False,
                    'video_id': None,
                    'error': str(e)
                })

                if not continue_on_error:
                    break

        successful = sum(1 for r in results if r['success'])
        logger.info(f"Batch processing complete: {successful}/{len(video_urls)} successful")

        return results

    def search(
        self,
        query: str,
        chunks_with_embeddings: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for relevant chunks using semantic similarity.

        Args:
            query: Search query
            chunks_with_embeddings: Chunks with embeddings
            top_k: Number of results to return

        Returns:
            Top-k most relevant chunks
        """
        return self.embedding_generator.search(
            query,
            chunks_with_embeddings,
            top_k=top_k
        )

    def get_statistics(self, result: Dict) -> Dict:
        """
        Get statistics about a processed video.

        Args:
            result: Pipeline result dictionary

        Returns:
            Statistics dictionary
        """
        stats = {
            'video_id': result.get('video_id'),
            'success': result.get('success'),
            'num_chunks': len(result.get('chunks', [])) if result.get('chunks') else 0,
            'processing_time': result.get('processing_time'),
        }

        if result.get('metadata'):
            metadata = result['metadata']
            stats.update({
                'title': metadata.get('title'),
                'duration': metadata.get('length'),
                'duration_formatted': self.metadata_extractor.format_duration(metadata.get('length', 0)),
                'is_long_video': self.metadata_extractor.is_long_video(metadata.get('length', 0)),
            })

        if result.get('transcript'):
            transcript = result['transcript']
            stats.update({
                'transcript_language': transcript.get('language'),
                'transcript_segments': len(transcript.get('transcript', [])),
                'auto_generated': transcript.get('auto_generated', False),
            })

        if result.get('chunks') and len(result['chunks']) > 0:
            chunk = result['chunks'][0]
            if 'embedding' in chunk:
                stats['embedding_dimension'] = chunk['embedding_dim']
                stats['embedding_model'] = chunk['embedding_model']

        return stats
