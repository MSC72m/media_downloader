"""YouTube metadata service implementation."""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from src.core.config import get_config, AppConfig
from src.core.interfaces import (
    IErrorNotifier,
    IYouTubeMetadataService,
    SubtitleInfo,
    YouTubeMetadata,
)
from ...utils.error_helpers import extract_error_context
from ...utils.logger import get_logger
from .info_extractor import YouTubeInfoExtractor
from .metadata_parser import YouTubeMetadataParser
from .subtitle_extractor import YouTubeSubtitleExtractor

logger = get_logger(__name__)


class YouTubeMetadataService(IYouTubeMetadataService):
    """Service for fetching YouTube video metadata using yt-dlp library."""

    def __init__(
        self,
        error_handler: Optional[IErrorNotifier] = None,
        config: AppConfig = get_config(),
    ):
        self.config = config
        self.error_handler = error_handler
        self.info_extractor = YouTubeInfoExtractor(error_handler=error_handler, config=config)
        self.metadata_parser = YouTubeMetadataParser(config=config)
        self.subtitle_extractor = YouTubeSubtitleExtractor(error_handler=error_handler, config=config)

    def fetch_metadata(
        self,
        url: str,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> Optional[YouTubeMetadata]:
        """Fetch basic metadata for a YouTube URL.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction

        Returns:
            YouTubeMetadata object or None if fetch fails
        """
        try:
            logger.info(f"[METADATA_SERVICE] Fetching metadata for URL: {url}")

            if not self.validate_url(url):
                error_msg = "Invalid YouTube URL"
                if self.error_handler:
                    self.error_handler.handle_service_failure("YouTube", "metadata fetch", error_msg, url)
                return YouTubeMetadata(error=error_msg)

            # Extract video information using yt-dlp library
            info = self.info_extractor.extract_info(url, cookie_path, browser)
            if not info:
                error_msg = "Failed to fetch video information"
                if self.error_handler:
                    self.error_handler.handle_service_failure("YouTube", "metadata fetch", error_msg, url)
                return YouTubeMetadata(error=error_msg)

            # Parse the info dict
            parsed_info = self.metadata_parser.parse_info(info)

            # Extract subtitle information (may enhance parsed_info)
            subtitle_data = self.subtitle_extractor.extract_subtitles(url, cookie_path, browser)
            if subtitle_data:
                parsed_info["subtitles"] = subtitle_data.get("subtitles", {})
                parsed_info["automatic_captions"] = subtitle_data.get("automatic_captions", {})

            # Extract formatted data
            available_qualities = self.metadata_parser.extract_qualities(parsed_info)
            available_formats = self.metadata_parser.extract_formats(parsed_info)
            available_subtitles = self.metadata_parser.extract_subtitles(parsed_info)

            return YouTubeMetadata(
                title=parsed_info.get("title", ""),
                duration=self.metadata_parser.format_duration(parsed_info.get("duration", 0)),
                view_count=self.metadata_parser.format_view_count(parsed_info.get("view_count", 0)),
                upload_date=self.metadata_parser.format_upload_date(parsed_info.get("upload_date", "")),
                channel=parsed_info.get("channel", ""),
                description=parsed_info.get("description", ""),
                thumbnail=parsed_info.get("thumbnail", ""),
                available_qualities=available_qualities,
                available_formats=available_formats,
                available_subtitles=available_subtitles,
                is_playlist="entries" in info,
                playlist_count=len(info.get("entries", [])),
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[METADATA_SERVICE] Error fetching metadata: {error_msg}", exc_info=True)
            if self.error_handler:
                error_context = extract_error_context(e, "YouTube", "metadata fetch", url)
                self.error_handler.handle_exception(e, "YouTube metadata fetch", "YouTube")
            return YouTubeMetadata(error=f"Failed to fetch metadata: {error_msg}")

    def get_available_qualities(self, url: str) -> List[str]:
        """Get available video qualities for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            return metadata.available_qualities if metadata else []
        except Exception as e:
            logger.error(f"[METADATA_SERVICE] Error fetching qualities: {str(e)}")
            return []

    def get_available_formats(self, url: str) -> List[str]:
        """Get available formats for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            return metadata.available_formats if metadata else []
        except Exception as e:
            logger.error(f"[METADATA_SERVICE] Error fetching formats: {str(e)}")
            return []

    def get_available_subtitles(self, url: str) -> List[SubtitleInfo]:
        """Get available subtitles for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            if not metadata or not metadata.available_subtitles:
                return []

            return [
                SubtitleInfo(
                    language_code=sub["language_code"],
                    language_name=sub["language_name"],
                    is_auto_generated=sub["is_auto_generated"],
                    url=sub["url"],
                )
                for sub in metadata.available_subtitles
            ]
        except Exception as e:
            logger.error(f"[METADATA_SERVICE] Error fetching subtitles: {str(e)}")
            return []

    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube URL."""
        return any(re.match(pattern, url) for pattern in self.config.youtube.url_patterns)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        try:
            parsed_url = urlparse(url)

            if parsed_url.hostname in self.config.youtube.youtube_domains:
                if parsed_url.path == "/watch":
                    query = parse_qs(parsed_url.query)
                    return query.get("v", [None])[0]
                elif parsed_url.path.startswith("/embed/"):
                    return parsed_url.path.split("/")[2]
                elif parsed_url.path.startswith("/v/"):
                    return parsed_url.path.split("/")[2]
            elif parsed_url.hostname == "youtu.be":
                return parsed_url.path[1:]  # Remove leading slash

            return None
        except Exception:
            return None
