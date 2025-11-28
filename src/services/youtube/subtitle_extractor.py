"""YouTube subtitle extractor using yt-dlp library."""

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
                    
                    # Extract video ID for validation
                    video_id = info.get("id", "")
                    
                    # Filter to only include subtitles with valid, downloadable HTTP URLs
                    # CRITICAL: Only return subtitles that actually exist and can be downloaded
                    # Must contain video ID or timedtext API pattern to be valid
                    # Config languages are ONLY for translation, NOT for showing all languages
                    valid_subtitles = {
                        lang: sub_list
                        for lang, sub_list in subtitles.items()
                        if (sub_list 
                            and isinstance(sub_list, list) 
                            and len(sub_list) > 0
                            and (url := sub_list[0].get("url", ""))
                            and isinstance(url, str)
                            and (url_stripped := url.strip())
                            and url_stripped
                            and url_stripped.startswith("http")
                            and len(url_stripped) > 50  # YouTube subtitle URLs are longer
                            and ("timedtext" in url_stripped or (video_id and video_id in url_stripped)))
                    }
                    
                    valid_auto = {
                        lang: sub_list
                        for lang, sub_list in automatic_captions.items()
                        if (sub_list 
                            and isinstance(sub_list, list) 
                            and len(sub_list) > 0
                            and (url := sub_list[0].get("url", ""))
                            and isinstance(url, str)
                            and (url_stripped := url.strip())
                            and url_stripped
                            and url_stripped.startswith("http")
                            and len(url_stripped) > 50  # YouTube subtitle URLs are longer
                            and ("timedtext" in url_stripped or (video_id and video_id in url_stripped)))
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

