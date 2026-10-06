"""
Metadata extraction module using pytube.
Extracts video metadata like title, author, duration, views, etc.
"""

from pytube import YouTube
from typing import Dict, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extracts metadata from YouTube videos using pytube."""

    def __init__(self):
        """Initialize the metadata extractor."""
        pass

    def extract(self, video_url: str) -> Dict:
        """
        Extract metadata from a YouTube video.

        Args:
            video_url: YouTube URL or video ID

        Returns:
            Dictionary containing:
                - success: bool
                - video_id: str
                - title: str
                - author: str
                - length: int (duration in seconds)
                - views: int
                - publish_date: datetime
                - description: str
                - thumbnail_url: str
                - keywords: List[str]
                - error: str (if success is False)
        """
        try:
            # Handle video ID vs full URL
            if not video_url.startswith('http'):
                video_url = f'https://www.youtube.com/watch?v={video_url}'

            yt = YouTube(video_url)

            return {
                'success': True,
                'video_id': yt.video_id,
                'title': yt.title,
                'author': yt.author,
                'length': yt.length,
                'views': yt.views,
                'publish_date': yt.publish_date,
                'description': yt.description,
                'thumbnail_url': yt.thumbnail_url,
                'keywords': yt.keywords or [],
                'rating': getattr(yt, 'rating', None),
                'channel_url': yt.channel_url,
                'error': None
            }

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {
                'success': False,
                'video_id': None,
                'title': None,
                'author': None,
                'length': None,
                'views': None,
                'publish_date': None,
                'description': None,
                'thumbnail_url': None,
                'keywords': None,
                'rating': None,
                'channel_url': None,
                'error': f'Error extracting metadata: {str(e)}'
            }

    def format_duration(self, seconds: int) -> str:
        """
        Format duration in seconds to HH:MM:SS.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"

    def is_long_video(self, length: int, threshold: int = 3600) -> bool:
        """
        Check if video is considered long.

        Args:
            length: Video length in seconds
            threshold: Threshold in seconds (default 1 hour)

        Returns:
            True if video is longer than threshold
        """
        return length > threshold
