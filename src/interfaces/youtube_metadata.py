"""Interface for YouTube metadata service."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class YouTubeMetadata(ABC):
    """Model representing YouTube video metadata."""

    def __init__(self, **kwargs):
        self.title: str = kwargs.get('title', '')
        self.duration: str = kwargs.get('duration', '')
        self.view_count: str = kwargs.get('view_count', '')
        self.upload_date: str = kwargs.get('upload_date', '')
        self.channel: str = kwargs.get('channel', '')
        self.description: str = kwargs.get('description', '')
        self.thumbnail: str = kwargs.get('thumbnail', '')
        self.available_qualities: List[str] = kwargs.get('available_qualities', [])
        self.available_formats: List[str] = kwargs.get('available_formats', [])
        self.available_subtitles: List[Dict[str, Any]] = kwargs.get('available_subtitles', [])
        self.is_playlist: bool = kwargs.get('is_playlist', False)
        self.playlist_count: int = kwargs.get('playlist_count', 0)
        self.error: Optional[str] = kwargs.get('error')


class SubtitleInfo:
    """Model representing subtitle information."""

    def __init__(self, language_code: str, language_name: str,
                 is_auto_generated: bool, url: str):
        self.language_code = language_code
        self.language_name = language_name
        self.is_auto_generated = is_auto_generated
        self.url = url


class IYouTubeMetadataService(ABC):
    """Interface for YouTube metadata service."""

    @abstractmethod
    def fetch_metadata(
        self,
        url: str,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> Optional[YouTubeMetadata]:
        """Fetch metadata for a YouTube URL.
        
        Args:
            url: YouTube URL
            cookie_path: Optional path to cookie file
            browser: Optional browser name for cookie extraction
        """
        pass

    @abstractmethod
    def get_available_qualities(self, url: str) -> List[str]:
        """Get available video qualities for a YouTube URL."""
        pass

    @abstractmethod
    def get_available_formats(self, url: str) -> List[str]:
        """Get available formats for a YouTube URL."""
        pass

    @abstractmethod
    def get_available_subtitles(self, url: str) -> List[SubtitleInfo]:
        """Get available subtitles for a YouTube URL."""
        pass

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube URL."""
        pass

    @abstractmethod
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        pass
