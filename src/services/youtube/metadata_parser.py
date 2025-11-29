import re
from typing import Any

from src.core.config import AppConfig, get_config
from src.core.interfaces import IParser
from src.services.youtube.subtitle_parser import YouTubeSubtitleParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

_YOUTUBE_URL_PATTERN = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|v/)|youtu\.be/)([a-zA-Z0-9_-]{11})",
    re.IGNORECASE,
)


class YouTubeMetadataParser(IParser):
    """Parses and formats YouTube metadata from yt-dlp info dict."""

    def __init__(self, config: AppConfig = get_config()):
        self.config = config
        self.subtitle_parser = YouTubeSubtitleParser(config)

    def validate(self, url: str, context: dict[str, Any] | None = None) -> bool:
        """Validate if a YouTube URL is valid and processable.

        Args:
            url: YouTube URL to validate
            context: Optional context dictionary (not used for URL validation)

        Returns:
            True if URL is a valid YouTube URL, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        return bool(_YOUTUBE_URL_PATTERN.search(url))

    def parse(
        self, data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Parse metadata info dict into standardized format.

        Args:
            data: Raw info dict from yt-dlp (or dict with 'info' key)
            context: Optional context dictionary (not currently used)

        Returns:
            List containing a single parsed metadata dict
        """
        info = data if isinstance(data, dict) and "title" in data else data.get("info", data)

        parsed = self.parse_info(info)
        return [parsed]

    def parse_info(self, info: dict[str, Any]) -> dict[str, Any]:
        """Parse yt-dlp info dict into standardized format.

        Args:
            info: Raw info dict from yt-dlp

        Returns:
            Parsed metadata dict
        """
        return {
            "title": info.get("title", ""),
            "duration": int(info.get("duration", 0)),
            "view_count": info.get("view_count", 0),
            "upload_date": info.get("upload_date", ""),
            "channel": info.get("channel", "") or info.get("uploader", ""),
            "description": info.get("description", ""),
            "thumbnail": info.get("thumbnail", ""),
            "subtitles": info.get("subtitles", {}),
            "automatic_captions": info.get("automatic_captions", {}),
        }

    def format_duration(self, duration_seconds: int) -> str:
        """Format duration in seconds to human readable format."""
        if not duration_seconds:
            return "Unknown"

        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def format_view_count(self, view_count: int) -> str:
        """Format view count to human readable format."""
        if not view_count:
            return "0 views"

        if view_count >= 1_000_000:
            return f"{view_count / 1_000_000:.1f}M views"
        if view_count >= 1_000:
            return f"{view_count / 1_000:.1f}K views"
        return f"{view_count} views"

    def format_upload_date(self, upload_date: str) -> str:
        """Format upload date from YYYYMMDD to readable format."""
        if not upload_date or len(upload_date) != 8:
            return "Unknown date"

        try:
            year = upload_date[:4]
            month = upload_date[4:6]
            day = upload_date[6:8]
            return f"{month}/{day}/{year}"
        except Exception:
            return "Unknown date"

    def extract_qualities(self, info: dict[str, Any]) -> list[str]:
        """Return standard video qualities."""
        return self.config.youtube.supported_qualities

    def extract_formats(self, info: dict[str, Any]) -> list[str]:
        """Extract available format options.

        Returns user-friendly format names from config, not internal values.
        Internal values are mapped in the dialog.
        """
        return self.config.ui.format_options

    def extract_subtitles(self, info: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract subtitle information from info dict.

        Returns empty list if no subtitles are available.
        If no subtitles are selected in UI, it's automatically treated as "None".
        Only returns subtitles with valid, downloadable URLs containing video ID or timedtext pattern.
        """
        manual_subs = info.get("subtitles", {}) or {}
        auto_subs = info.get("automatic_captions", {}) or {}
        video_id = info.get("id", "")

        data = {
            "subtitles": manual_subs,
            "automatic_captions": auto_subs,
        }
        context = {"video_id": video_id}
        return self.subtitle_parser.parse(data, context)
