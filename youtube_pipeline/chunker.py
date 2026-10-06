"""
Text chunking module for splitting transcripts into manageable pieces.
Supports various chunking strategies with overlap for context preservation.
"""

from typing import List, Dict, Optional
import re


class Chunker:
    """Splits text into chunks for embedding generation."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        strategy: str = "fixed"
    ):
        """
        Initialize the chunker.

        Args:
            chunk_size: Maximum number of characters per chunk
            chunk_overlap: Number of characters to overlap between chunks
            strategy: Chunking strategy ('fixed', 'sentence', 'paragraph')
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.strategy = strategy

        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")

    def chunk_transcript(
        self,
        transcript_data: List[Dict],
        include_timestamps: bool = True
    ) -> List[Dict]:
        """
        Chunk transcript data with timestamps.

        Args:
            transcript_data: List of transcript segments with 'text', 'start', 'duration'
            include_timestamps: Whether to include timestamp info in chunks

        Returns:
            List of chunks with text, start_time, end_time, and segment indices
        """
        if not transcript_data:
            return []

        # First, get full text
        full_text = " ".join([seg['text'] for seg in transcript_data])

        # Chunk the text
        text_chunks = self.chunk(full_text)

        # Map chunks back to timestamps
        chunks_with_metadata = []
        current_char_pos = 0

        for chunk_text in text_chunks:
            chunk_start_char = current_char_pos
            chunk_end_char = current_char_pos + len(chunk_text)

            # Find corresponding transcript segments
            char_counter = 0
            start_time = None
            end_time = None
            segment_indices = []

            for idx, segment in enumerate(transcript_data):
                segment_start_char = char_counter
                segment_end_char = char_counter + len(segment['text']) + 1  # +1 for space

                # Check if segment overlaps with chunk
                if segment_end_char > chunk_start_char and segment_start_char < chunk_end_char:
                    if start_time is None:
                        start_time = segment['start']
                    end_time = segment['start'] + segment['duration']
                    segment_indices.append(idx)

                char_counter = segment_end_char

            chunk_data = {
                'text': chunk_text,
                'char_start': chunk_start_char,
                'char_end': chunk_end_char,
            }

            if include_timestamps:
                chunk_data.update({
                    'start_time': start_time,
                    'end_time': end_time,
                    'segment_indices': segment_indices
                })

            chunks_with_metadata.append(chunk_data)

            # Move to next chunk (accounting for overlap)
            current_char_pos += len(chunk_text) - self.chunk_overlap

        return chunks_with_metadata

    def chunk(self, text: str) -> List[str]:
        """
        Chunk text according to the selected strategy.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if not text:
            return []

        if self.strategy == "fixed":
            return self._chunk_fixed(text)
        elif self.strategy == "sentence":
            return self._chunk_sentence(text)
        elif self.strategy == "paragraph":
            return self._chunk_paragraph(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.strategy}")

    def _chunk_fixed(self, text: str) -> List[str]:
        """
        Fixed-size chunking with overlap.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # Try to break at word boundary if not at end
            if end < len(text):
                last_space = chunk.rfind(' ')
                if last_space > self.chunk_size * 0.8:  # Only if space is in last 20%
                    chunk = chunk[:last_space]
                    end = start + last_space

            chunks.append(chunk.strip())

            # Move start position (accounting for overlap)
            start = end - self.chunk_overlap

            # Prevent infinite loop
            if start <= len(text) and end >= len(text):
                break

        return chunks

    def _chunk_sentence(self, text: str) -> List[str]:
        """
        Chunk by sentences, respecting chunk_size limits.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If single sentence exceeds chunk_size, split it
            if sentence_len > self.chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                # Split long sentence into fixed chunks
                chunks.extend(self._chunk_fixed(sentence))
                continue

            # Add sentence to current chunk if it fits
            if current_size + sentence_len <= self.chunk_size:
                current_chunk.append(sentence)
                current_size += sentence_len + 1  # +1 for space
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(' '.join(current_chunk))

                # Handle overlap by including last few sentences
                overlap_size = 0
                overlap_sentences = []
                for s in reversed(current_chunk):
                    if overlap_size + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_size += len(s) + 1
                    else:
                        break

                current_chunk = overlap_sentences + [sentence]
                current_size = sum(len(s) for s in current_chunk) + len(current_chunk) - 1

        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _chunk_paragraph(self, text: str) -> List[str]:
        """
        Chunk by paragraphs, respecting chunk_size limits.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = []
        current_size = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_len = len(paragraph)

            # If single paragraph exceeds chunk_size, use sentence chunking
            if paragraph_len > self.chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0

                chunks.extend(self._chunk_sentence(paragraph))
                continue

            # Add paragraph to current chunk if it fits
            if current_size + paragraph_len <= self.chunk_size:
                current_chunk.append(paragraph)
                current_size += paragraph_len + 2  # +2 for \n\n
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))

                current_chunk = [paragraph]
                current_size = paragraph_len

        # Add final chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks
