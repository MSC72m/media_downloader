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
                    if info:
                        subtitles = info.get("subtitles", {})
                        automatic_captions = info.get("automatic_captions", {})

                        if subtitles or automatic_captions:
                            logger.info(
                                f"[SUBTITLE_EXTRACTOR] Found {len(subtitles)} manual and "
                                f"{len(automatic_captions)} auto subtitles with {client} client"
                            )
                            return {
                                "subtitles": subtitles,
                                "automatic_captions": automatic_captions,
                            }
            except Exception as e:
                logger.debug(f"[SUBTITLE_EXTRACTOR] {client} client subtitle extraction error: {e}")
                continue

        # Fallback: Assume English auto captions are available
        logger.info("[SUBTITLE_EXTRACTOR] Using fallback - assuming English auto captions")
        return {"subtitles": {}, "automatic_captions": {"en": [{"url": ""}]}}

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

