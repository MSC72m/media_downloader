"""YouTube subtitle parser implementation."""

import re
from itertools import chain
from typing import Any, Dict, List, Optional

from src.core.config import AppConfig, get_config
from src.interfaces.parser import IParser
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Pre-compile regex patterns once at module level for efficiency
# Pattern to match lang=XX parameter (actual subtitle language)
_LANG_PARAM_PATTERN = re.compile(r'[?&]lang=([^&"\']+?)(?:[&"\']|$)', re.IGNORECASE)
# Pattern to match tlang=XX parameter (translation option)
_TLANG_PARAM_PATTERN = re.compile(r'[?&]tlang=([^&"\']+?)(?:[&"\']|$)', re.IGNORECASE)


class YouTubeSubtitleParser(IParser):
    """YouTube-specific implementation of subtitle parser."""

    def __init__(self, config: AppConfig = get_config()):
        self.config = config

    def validate(self, url: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Validate if a subtitle URL is valid and downloadable.
        
        Args:
            url: Subtitle URL to validate
            context: Dictionary with 'video_id' and 'language_code' keys
            
        Returns:
            True if URL is valid and language_code matches 'lang=' parameter,
            False otherwise (rejects translation-only URLs with 'tlang=')
        """
        if not context:
            return False
        
        video_id = context.get("video_id", "")
        language_code = context.get("language_code", "")
        
        return self._is_valid_subtitle_url(url, video_id, language_code)

    def parse(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Parse subtitle dictionaries into formatted list.
        
        Args:
            data: Dictionary with 'subtitles' and 'automatic_captions' keys
            context: Dictionary with 'video_id' key
            
        Returns:
            List of validated subtitle dicts with language_code, language_name, 
            is_auto_generated, and url fields. Duplicates removed.
        """
        if not context:
            return []
        
        subtitles = data.get("subtitles", {}) or {}
        automatic_captions = data.get("automatic_captions", {}) or {}
        video_id = context.get("video_id", "")
        
        return self._parse_subtitles(subtitles, automatic_captions, video_id)

    def _is_valid_subtitle_url(self, url: str, video_id: str, language_code: str) -> bool:
        """Check if subtitle URL is actually valid and downloadable.
        
        CRITICAL: Only accept URLs where lang_code matches the 'lang=' parameter,
        NOT 'tlang='. 'tlang=' indicates translation options, not actual subtitles.
        Uses pre-compiled regex patterns for efficiency.
        
        Args:
            url: Subtitle URL to validate
            video_id: Video ID for validation
            language_code: Language code to match against URL parameters
            
        Returns:
            True if URL is valid and language_code matches 'lang=' parameter,
            False otherwise (rejects translation-only URLs with 'tlang=')
        """
        if not url or not isinstance(url, str):
            return False
        
        url_stripped = url.strip()
        # Must be valid YouTube subtitle API URL with ALL required components
        if not (url_stripped.startswith("https://www.youtube.com/api/timedtext")
                and len(url_stripped) > 100  # Real YouTube subtitle URLs are much longer
                and video_id in url_stripped  # Must contain video ID
                and "timedtext" in url_stripped  # Must be timedtext API
                and "fmt=" in url_stripped):  # Must have format parameter
            return False
        
        # Extract base language code for matching
        base_lang = language_code.split("-", 1)[0].lower()
        
        # Use pre-compiled regex to extract lang= and tlang= values efficiently
        # Extract all lang= values - use set comprehension for O(1) lookup and deduplication
        lang_matches = _LANG_PARAM_PATTERN.findall(url_stripped)
        # Normalize efficiently: lowercase and take first part before & or # (no loops, direct string ops)
        lang_values = {m.lower().partition('&')[0].partition('#')[0] for m in lang_matches}
        
        # Extract all tlang= values - use set comprehension for O(1) lookup and deduplication
        tlang_matches = _TLANG_PARAM_PATTERN.findall(url_stripped)
        # Normalize efficiently: lowercase and take first part before & or # (no loops, direct string ops)
        tlang_values = {m.lower().partition('&')[0].partition('#')[0] for m in tlang_matches}
        
        # Accept if lang_code matches a 'lang=' parameter value (actual subtitle in any language)
        # Reject if it only matches 'tlang=' (translation option)
        lang_matches = base_lang in lang_values
        tlang_only = base_lang in tlang_values and not lang_matches
        
        return lang_matches and not tlang_only

    def _parse_subtitles(
        self, 
        subtitles: Dict[str, Any], 
        automatic_captions: Dict[str, Any],
        video_id: str
    ) -> List[Dict[str, Any]]:
        """Parse and validate subtitle dictionaries into formatted list.
        
        Args:
            subtitles: Manual subtitles dict from yt-dlp
            automatic_captions: Automatic captions dict from yt-dlp
            video_id: Video ID for validation
            
        Returns:
            List of validated subtitle dicts with language_code, language_name, 
            is_auto_generated, and url fields. Duplicates removed.
        """
        # Single list comprehension processing both dicts via chain
        # CRITICAL: Only include subtitles with valid, downloadable YouTube API URLs
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
                ((lang, sub_list, False) for lang, sub_list in subtitles.items()),
                ((lang, sub_list, True) for lang, sub_list in automatic_captions.items()),
            )
            if (sub_list
                and isinstance(sub_list, list)
                and len(sub_list) > 0
                and (sub_url := sub_list[0].get("url", ""))
                and self._is_valid_subtitle_url(sub_url, video_id, lang_code))
        ]
        
        # Remove duplicates using set - deduplicate by (language_code, is_auto_generated) tuple
        seen = set()
        unique_result = []
        for item in result:
            # Create unique key: (language_code, is_auto_generated)
            key = (item["language_code"], item["is_auto_generated"])
            if key not in seen:
                seen.add(key)
                unique_result.append(item)
        
        logger.info(
            f"[YOUTUBE_SUBTITLE_PARSER] Extracted {len(unique_result)} unique valid subtitles "
            f"(from {len(subtitles)} manual, {len(automatic_captions)} auto raw entries, "
            f"{len(result) - len(unique_result)} duplicates removed)"
        )
        return unique_result

    def _get_language_name(self, lang_code: str) -> str:
        """Convert language code to readable language name.
        
        Returns full language name from config if available,
        otherwise returns the language code itself (not uppercase).
        """
        base_code = lang_code.split("-")[0].lower()
        return self.config.youtube.supported_languages.get(base_code, lang_code)

