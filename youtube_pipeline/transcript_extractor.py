"""
Transcript extraction module using youtube-transcript-api.
Handles missing transcripts and provides fallback options.
"""

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from typing import List, Dict, Optional
import re


class TranscriptExtractor:
    """Extracts transcripts from YouTube videos."""

    def __init__(self, languages: List[str] = None):
        """
        Initialize the transcript extractor.

        Args:
            languages: List of preferred languages (e.g., ['en', 'es']). Defaults to ['en'].
        """
        self.languages = languages or ['en']

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.

        Args:
            url: YouTube URL or video ID

        Returns:
            Video ID or None if invalid
        """
        # If it's already just an ID
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url

        # Regular YouTube URL patterns
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def extract(self, video_url: str) -> Dict:
        """
        Extract transcript from a YouTube video.

        Args:
            video_url: YouTube URL or video ID

        Returns:
            Dictionary containing:
                - success: bool
                - video_id: str
                - transcript: List of dict with 'text', 'start', 'duration'
                - language: str (language code of retrieved transcript)
                - error: str (if success is False)
        """
        video_id = self.extract_video_id(video_url)

        if not video_id:
            return {
                'success': False,
                'video_id': None,
                'transcript': None,
                'language': None,
                'error': 'Invalid YouTube URL or video ID'
            }

        try:
            # Try to get transcript in preferred languages
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try manual transcripts first
            try:
                for lang in self.languages:
                    try:
                        transcript = transcript_list.find_manually_created_transcript([lang])
                        data = transcript.fetch()
                        return {
                            'success': True,
                            'video_id': video_id,
                            'transcript': data,
                            'language': lang,
                            'error': None
                        }
                    except NoTranscriptFound:
                        continue
            except Exception:
                pass

            # Fall back to auto-generated transcripts
            try:
                for lang in self.languages:
                    try:
                        transcript = transcript_list.find_generated_transcript([lang])
                        data = transcript.fetch()
                        return {
                            'success': True,
                            'video_id': video_id,
                            'transcript': data,
                            'language': lang,
                            'error': None,
                            'auto_generated': True
                        }
                    except NoTranscriptFound:
                        continue
            except Exception:
                pass

            # If no preferred language found, get any available transcript
            try:
                transcript = transcript_list.find_transcript(['en'])
                data = transcript.fetch()
                return {
                    'success': True,
                    'video_id': video_id,
                    'transcript': data,
                    'language': 'en',
                    'error': None
                }
            except NoTranscriptFound:
                pass

            return {
                'success': False,
                'video_id': video_id,
                'transcript': None,
                'language': None,
                'error': 'No transcript available in requested languages'
            }

        except TranscriptsDisabled:
            return {
                'success': False,
                'video_id': video_id,
                'transcript': None,
                'language': None,
                'error': 'Transcripts are disabled for this video'
            }
        except Exception as e:
            return {
                'success': False,
                'video_id': video_id,
                'transcript': None,
                'language': None,
                'error': f'Error extracting transcript: {str(e)}'
            }

    def get_full_text(self, transcript_data: List[Dict]) -> str:
        """
        Combine transcript segments into full text.

        Args:
            transcript_data: List of transcript segments

        Returns:
            Full transcript text
        """
        if not transcript_data:
            return ""

        return " ".join([segment['text'] for segment in transcript_data])
