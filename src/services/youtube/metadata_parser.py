"""YouTube metadata parser and formatter."""

import re
from itertools import chain
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
        """Extract available format options.
        
        Returns user-friendly format names from config, not internal values.
        Internal values are mapped in the dialog.
        """
        # Return user-friendly format names from config
        return self.config.ui.format_options

    def extract_subtitles(self, info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract subtitle information from info dict.
        
        Returns empty list if no subtitles are available.
        If no subtitles are selected in UI, it's automatically treated as "None".
        Only returns subtitles with valid, downloadable URLs containing video ID or timedtext pattern.
        """
        # Chain both subtitle dicts and process in a single loop
        manual_subs = info.get("subtitles", {}) or {}
        auto_subs = info.get("automatic_captions", {}) or {}
        video_id = info.get("id", "")
        
        # Helper function for strict validation - only real YouTube subtitle API URLs
        def _is_valid_subtitle_url(url: str, vid_id: str, lang_code: str) -> bool:
            """Check if subtitle URL is actually valid and downloadable.
            
            CRITICAL: Only accept URLs where lang_code matches the 'lang=' parameter,
            NOT 'tlang='. 'tlang=' indicates translation options, not actual subtitles.
            """
            if not url or not isinstance(url, str):
                return False
            
            url_stripped = url.strip()
            # Must be valid YouTube subtitle API URL with ALL required components
            if not (url_stripped.startswith("https://www.youtube.com/api/timedtext")
                    and len(url_stripped) > 100  # Real YouTube subtitle URLs are much longer
                    and vid_id in url_stripped  # Must contain video ID
                    and "timedtext" in url_stripped  # Must be timedtext API
                    and "fmt=" in url_stripped):  # Must have format parameter
                return False
            
            # CRITICAL: Only accept if lang_code matches 'lang=' parameter (actual subtitle)
            # NOT 'tlang=' (translation option). Use regex for efficient single-pass matching.
            # Accept ALL actual subtitles (English, Spanish, French, etc.) - only reject translations.
            base_lang = lang_code.split("-")[0].lower()
            
            # Single regex pattern to check both lang= and tlang= in one pass (more efficient)
            # Pattern: (?i) ensures case-insensitive, captures lang value, checks for tlang separately
            # Match lang=XX (not preceded by t) - this is the actual subtitle language
            lang_match_pattern = re.compile(rf'[?&]lang=({re.escape(base_lang)})(?:[&"\']|$)', re.IGNORECASE)
            # Match tlang=XX - this is a translation option
            tlang_match_pattern = re.compile(rf'[?&]tlang=({re.escape(base_lang)})(?:[&"\']|$)', re.IGNORECASE)
            
            # Check if lang_code matches lang= parameter (actual subtitle in any language)
            lang_matches = bool(lang_match_pattern.search(url_stripped))
            # Check if lang_code only matches tlang= (translation option, not actual subtitle)
            tlang_only = bool(tlang_match_pattern.search(url_stripped)) and not lang_matches
            
            # Accept if it's an actual subtitle (lang= matches), reject if it's only a translation (tlang= only)
            return lang_matches and not tlang_only
        
        # Single list comprehension processing both dicts via chain
        # CRITICAL: Only include subtitles with valid, downloadable YouTube API URLs
        # YouTube returns entries for all languages, but most don't have actual subtitle files
        # Config languages are ONLY for translation/mapping, NOT for showing all languages
        result = [
            {
                "language_code": lang_code,
                "language_name": (
                    f"{self._get_language_name(lang_code)} (Auto)"
                    if is_auto
                    else self._get_language_name(lang_code)
                ),
                "is_auto_generated": is_auto,
                "url": sub_url,
            }
            for lang_code, sub_list, is_auto in chain(
                ((lang, sub_list, False) for lang, sub_list in manual_subs.items()),
                ((lang, sub_list, True) for lang, sub_list in auto_subs.items()),
            )
            if (sub_list
                and isinstance(sub_list, list)
                and len(sub_list) > 0
                and (sub_url := sub_list[0].get("url", ""))
                and _is_valid_subtitle_url(sub_url, video_id, lang_code))
        ]
        
        logger.info(
            f"[METADATA_PARSER] Extracted {len(result)} valid subtitles "
            f"(from {len(manual_subs)} manual, {len(auto_subs)} auto raw entries)"
        )
        return result

    def _get_language_name(self, lang_code: str) -> str:
        """Convert language code to readable language name.
        
        Returns full language name from config if available,
        otherwise returns the language code itself (not uppercase).
        Config languages are only for translation/mapping, not for showing all languages.
        """
        base_code = lang_code.split("-")[0].lower()
        return self.config.youtube.supported_languages.get(base_code, lang_code)

