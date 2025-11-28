"""YouTube metadata parser and formatter."""

import re
from typing import Any, Dict, List, Optional

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeMetadataParser:
    """Parses and formats YouTube metadata from yt-dlp info dict."""

    def __init__(self, config: AppConfig = get_config()):
        self.config = config

    def parse_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
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
        elif view_count >= 1_000:
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

    def extract_qualities(self, info: Dict[str, Any]) -> List[str]:
        """Return standard video qualities."""
        return self.config.youtube.supported_qualities

    def extract_formats(self, info: Dict[str, Any]) -> List[str]:
        """Extract available format options."""
        # Always return the 4 format options the user can choose from
        return ["video_only", "video_audio", "audio_only", "separate"]

    def extract_subtitles(self, info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract subtitle information from info dict."""
        subtitles = []

        # Add "None" option first
        subtitles.append(
            {
                "language_code": "none",
                "language_name": "None",
                "is_auto_generated": False,
                "url": "",
            }
        )

        # Get manual subtitles
        manual_subs = info.get("subtitles", {})
        for lang_code, sub_list in manual_subs.items():
            if sub_list:
                subtitles.append(
                    {
                        "language_code": lang_code,
                        "language_name": self._get_language_name(lang_code),
                        "is_auto_generated": False,
                        "url": sub_list[0].get("url", "") if isinstance(sub_list, list) else "",
                    }
                )

        # Get automatic subtitles
        auto_subs = info.get("automatic_captions", {})
        for lang_code, sub_list in auto_subs.items():
            if sub_list:
                subtitles.append(
                    {
                        "language_code": lang_code,
                        "language_name": f"{self._get_language_name(lang_code)} (Auto)",
                        "is_auto_generated": True,
                        "url": sub_list[0].get("url", "") if isinstance(sub_list, list) else "",
                    }
                )

        return subtitles

    def _get_language_name(self, lang_code: str) -> str:
        """Convert language code to readable language name."""
        base_code = lang_code.split("-")[0].lower()
        return self.config.youtube.supported_languages.get(base_code, lang_code)

