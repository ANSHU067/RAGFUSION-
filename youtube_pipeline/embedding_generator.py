"""
Embedding generation module using sentence-transformers.
Generates dense vector embeddings from text chunks.
"""

from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings from text chunks using sentence-transformers."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        batch_size: int = 32
    ):
        """
        Initialize the embedding generator.

        Args:
            model_name: Name of the sentence-transformer model
            device: Device to use ('cuda', 'cpu', or None for auto)
            batch_size: Batch size for encoding
        """
        self.model_name = model_name
        self.batch_size = batch_size

        try:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name, device=device)
            logger.info(f"Model loaded successfully on device: {self.model.device}")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise

    def generate(
        self,
        chunks: List[Dict],
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Generate embeddings for text chunks.

        Args:
            chunks: List of chunk dictionaries containing 'text' field
            show_progress: Whether to show progress bar

        Returns:
            List of chunks with added 'embedding' field
        """
        if not chunks:
            return []

        try:
            # Extract text from chunks
            texts = [chunk['text'] for chunk in chunks]

            # Generate embeddings
            logger.info(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )

            # Add embeddings to chunks
            enriched_chunks = []
            for chunk, embedding in zip(chunks, embeddings):
                enriched_chunk = chunk.copy()
                enriched_chunk['embedding'] = embedding
                enriched_chunk['embedding_model'] = self.model_name
                enriched_chunk['embedding_dim'] = len(embedding)
                enriched_chunks.append(enriched_chunk)

            logger.info(f"Generated {len(enriched_chunks)} embeddings")
            return enriched_chunks

        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise

    def generate_single(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        metric: str = "cosine"
    ) -> float:
        """
        Compute similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            metric: Similarity metric ('cosine' or 'euclidean')

        Returns:
            Similarity score
        """
        if metric == "cosine":
            # Cosine similarity
            return float(
                np.dot(embedding1, embedding2) /
                (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
            )
        elif metric == "euclidean":
            # Euclidean distance (inverted for similarity)
            return float(1 / (1 + np.linalg.norm(embedding1 - embedding2)))
        else:
            raise ValueError(f"Unknown metric: {metric}")

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by the model.

        Returns:
            Embedding dimension
        """
        return self.model.get_sentence_embedding_dimension()

    def search(
        self,
        query: str,
        chunks_with_embeddings: List[Dict],
        top_k: int = 5,
        metric: str = "cosine"
    ) -> List[Dict]:
        """
        Search for most similar chunks to a query.

        Args:
            query: Search query
            chunks_with_embeddings: List of chunks with embeddings
            top_k: Number of top results to return
            metric: Similarity metric

        Returns:
            List of top-k most similar chunks with similarity scores
        """
        if not chunks_with_embeddings:
            return []

        # Generate query embedding
        query_embedding = self.generate_single(query)

        # Compute similarities
        results = []
        for chunk in chunks_with_embeddings:
            similarity = self.compute_similarity(
                query_embedding,
                chunk['embedding'],
                metric=metric
            )
            result = chunk.copy()
            result['similarity'] = similarity
            results.append(result)

        # Sort by similarity and return top-k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
