"""YouTube info extractor using yt-dlp library directly."""

from typing import Any, Dict, List, Optional

import yt_dlp

from src.core.config import AppConfig, get_config
from src.interfaces.service_interfaces import IErrorHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeInfoExtractor:
    """Extracts YouTube video information using yt-dlp library."""

    def __init__(
        self,
        error_handler: Optional[IErrorHandler] = None,
        config: AppConfig = get_config(),
    ):
        self.error_handler = error_handler
        self.config = config

    def extract_info(
        self,
        url: str,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract video information using yt-dlp library.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction

        Returns:
            Video info dict or None if extraction fails
        """
        # Try primary method with cookies
        info = self._extract_with_cookies(url, cookie_path, browser)
        if info:
            return info

        # Fallback: Try with browser cookies
        if cookie_path or browser:
            logger.info("[INFO_EXTRACTOR] Primary extraction failed, trying browser cookies...")
            info = self._extract_with_browser_cookies(url, browser)
            if info:
                return info

        # Final fallback: Try different client types
        logger.info("[INFO_EXTRACTOR] Trying different client types...")
        return self._extract_with_client_fallback(url)

    def _extract_with_cookies(
        self,
        url: str,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract info with cookie file or browser cookies."""
        opts = self._build_options(cookie_path, browser)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=False)
                if info:
                    logger.info("[INFO_EXTRACTOR] Successfully extracted info with cookies")
                    return info
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.warning(f"[INFO_EXTRACTOR] Download error: {error_msg}")
            if self._is_cookie_error(error_msg):
                logger.warning("[INFO_EXTRACTOR] Cookie error detected")
        except Exception as e:
            logger.warning(f"[INFO_EXTRACTOR] Extraction error: {e}", exc_info=True)

        return None

    def _extract_with_browser_cookies(
        self, url: str, browser: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Extract info using browser cookies."""
        browser_name = browser or "chrome"
        opts = self._build_options(None, browser_name)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=False)
                if info:
                    logger.info(f"[INFO_EXTRACTOR] Successfully extracted info with {browser_name} cookies")
                    return info
        except Exception as e:
            logger.debug(f"[INFO_EXTRACTOR] Browser cookie extraction failed: {e}")

        return None

    def _extract_with_client_fallback(self, url: str) -> Optional[Dict[str, Any]]:
        """Try extraction with different YouTube client types."""
        clients = ["android", "ios", "tv_embedded", "web"]

        for client in clients:
            try:
                opts = self._build_options(None, None, client)
                with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                    info = ydl.extract_info(url, download=False)
                    if info:
                        logger.info(f"[INFO_EXTRACTOR] Successfully extracted info with {client} client")
                        return info
            except Exception as e:
                logger.debug(f"[INFO_EXTRACTOR] {client} client failed: {e}")

        return None

    def _build_options(
        self,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
        client: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build yt-dlp options for metadata extraction."""
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
        }

        # Add cookies
        if cookie_path:
            opts["cookiefile"] = cookie_path
            logger.debug(f"[INFO_EXTRACTOR] Using cookie file: {cookie_path}")
        elif browser:
            opts["cookiesfrombrowser"] = (browser,)
            logger.debug(f"[INFO_EXTRACTOR] Using browser cookies: {browser}")

        # Set client type
        client_type = client or "web"
        opts["extractor_args"] = {"youtube": {"player_client": [client_type]}}

        return opts

    def _is_cookie_error(self, error_msg: str) -> bool:
        """Check if error is related to cookies."""
        cookie_indicators = [
            "Sign in to confirm",
            "bot",
            "Use --cookies",
            "authentication",
            "unauthorized",
        ]
        error_lower = error_msg.lower()
        return any(indicator.lower() in error_lower for indicator in cookie_indicators)

