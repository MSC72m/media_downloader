"""YouTube subtitle extractor using yt-dlp library."""

import re
from typing import Any, Dict, Optional

import yt_dlp

from src.core.config import AppConfig, get_config
from src.interfaces.service_interfaces import IErrorHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeSubtitleExtractor:
    """Extracts YouTube subtitle information using yt-dlp library."""

    def __init__(
        self,
        error_handler: Optional[IErrorHandler] = None,
        config: AppConfig = get_config(),
    ):
        self.error_handler = error_handler
        self.config = config

    def extract_subtitles(
        self,
        url: str,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract subtitle information from YouTube video.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction

        Returns:
            Dict with 'subtitles' and 'automatic_captions' keys
        """
        # Try multiple client types in order: android, ios, tv_embedded
        clients_to_try = ["android", "ios", "tv_embedded"]
        
        for client in clients_to_try:
            opts = self._build_options(cookie_path, browser, client)
            logger.debug(f"[SUBTITLE_EXTRACTOR] Trying subtitle extraction with {client} client")
            
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                    info = ydl.extract_info(url, download=False)
                    if not info:
                        continue
                    
                    subtitles = info.get("subtitles", {}) or {}
                    automatic_captions = info.get("automatic_captions", {}) or {}
                    
                    # Extract video ID for strict validation
                    video_id = info.get("id", "")
                    
                    # CRITICAL: Only return subtitles that actually exist and are downloadable
                    # YouTube returns entries for all languages, but most are translation options (tlang=)
                    # not actual subtitles (lang=). Only accept where lang_code matches 'lang=' parameter.
                    # Config languages are ONLY for translation, NOT for showing all languages
                    def _is_valid_subtitle_entry(sub_entry: Dict[str, Any], vid_id: str, lang_code: str) -> bool:
                        """Check if subtitle entry is actually valid and downloadable.
                        
                        CRITICAL: Only accept URLs where lang_code matches the 'lang=' parameter,
                        NOT 'tlang='. 'tlang=' indicates translation options, not actual subtitles.
                        """
                        if not sub_entry or not isinstance(sub_entry, dict):
                            return False
                        
                        url = sub_entry.get("url", "")
                        if not url or not isinstance(url, str):
                            return False
                        
                        url_stripped = url.strip()
                        # Must be valid YouTube subtitle API URL with all required components
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
                    
                    valid_subtitles = {
                        lang: sub_list
                        for lang, sub_list in subtitles.items()
                        if (sub_list 
                            and isinstance(sub_list, list) 
                            and len(sub_list) > 0
                            and _is_valid_subtitle_entry(sub_list[0], video_id, lang))
                    }
                    
                    valid_auto = {
                        lang: sub_list
                        for lang, sub_list in automatic_captions.items()
                        if (sub_list 
                            and isinstance(sub_list, list) 
                            and len(sub_list) > 0
                            and _is_valid_subtitle_entry(sub_list[0], video_id, lang))
                    }

                    if not (valid_subtitles or valid_auto):
                        continue
                    
                    logger.info(
                        f"[SUBTITLE_EXTRACTOR] Found {len(valid_subtitles)} manual and "
                        f"{len(valid_auto)} auto subtitles with {client} client "
                        f"(filtered from {len(subtitles)} manual, {len(automatic_captions)} auto)"
                    )
                    return {
                        "subtitles": valid_subtitles,
                        "automatic_captions": valid_auto,
                    }
            except Exception as e:
                logger.debug(f"[SUBTITLE_EXTRACTOR] {client} client subtitle extraction error: {e}")
                continue

        # No subtitles found - return empty dicts
        logger.info("[SUBTITLE_EXTRACTOR] No subtitles found for this video")
        return {"subtitles": {}, "automatic_captions": {}}

    def _build_options(
        self,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
        client: str = "android",
    ) -> Dict[str, Any]:
        """Build yt-dlp options for subtitle extraction."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "extractor_args": {"youtube": {"player_client": [client]}},
        }

        if cookie_path:
            opts["cookiefile"] = cookie_path
        elif browser:
            opts["cookiesfrombrowser"] = (browser,)

        return opts

