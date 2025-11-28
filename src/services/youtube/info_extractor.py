"""YouTube info extractor using yt-dlp library directly."""

from typing import Any, Dict, Optional
from pathlib import Path

import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeInfoExtractor:
    """Extracts YouTube video information using yt-dlp library."""

    def __init__(
        self,
        error_handler: Optional[IErrorNotifier] = None,
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
        # Try multiple client types in order: android, ios, tv_embedded, web
        # This matches the mobile cookie generation and provides fallbacks
        clients_to_try = ["android", "ios", "tv_embedded", "web"]

        for client in clients_to_try:
            logger.info(f"[INFO_EXTRACTOR] Trying extraction with {client} client...")
            info = self._extract_with_cookies(url, cookie_path, browser, client)
            if info:
                return info

        # Fallback: Try with browser cookies
        if cookie_path or browser:
            logger.info(
                "[INFO_EXTRACTOR] Cookie file failed, trying browser cookies..."
            )
            info = self._extract_with_browser_cookies(url, browser)
            if info:
                return info

        # Final fallback: Try different client types without cookies
        logger.info("[INFO_EXTRACTOR] Trying different client types without cookies...")
        return self._extract_with_client_fallback(url)

    def _extract_with_cookies(
        self,
        url: str,
        cookie_path: Optional[str] = None,
        browser: Optional[str] = None,
        client: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extract info with cookie file or browser cookies.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction
            client: Optional client type to use (defaults to 'web')
        """

        # Verify cookie file exists and is readable
        if cookie_path:
            cookie_file = Path(cookie_path)
            if not cookie_file.exists():
                logger.warning(
                    f"[INFO_EXTRACTOR] Cookie file does not exist: {cookie_path}"
                )
                return None
            if cookie_file.stat().st_size == 0:
                logger.warning(f"[INFO_EXTRACTOR] Cookie file is empty: {cookie_path}")
                return None

        opts = self._build_options(cookie_path, browser, client)
        client_used = client or "web"
        logger.info(
            f"[INFO_EXTRACTOR] Attempting extraction with cookies (client: {client_used}, cookie_file: {opts.get('cookiefile', 'None')})"
        )

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=False)
                if info:
                    logger.info(
                        f"[INFO_EXTRACTOR] Successfully extracted info with cookies (client: {client_used})"
                    )
                    return info
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.warning(
                f"[INFO_EXTRACTOR] Download error with {client_used} client: {error_msg[:200]}"
            )
            if self._is_cookie_error(error_msg):
                logger.warning(
                    f"[INFO_EXTRACTOR] Cookie error detected with {client_used} - cookies may be invalid or expired"
                )
        except Exception as e:
            logger.warning(
                f"[INFO_EXTRACTOR] Extraction error with {client_used}: {e}",
                exc_info=True,
            )

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
                    logger.info(
                        f"[INFO_EXTRACTOR] Successfully extracted info with {browser_name} cookies"
                    )
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
                        logger.info(
                            f"[INFO_EXTRACTOR] Successfully extracted info with {client} client"
                        )
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
        from pathlib import Path

        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
        }

        # Add cookies - verify file exists if cookie_path is provided
        if cookie_path:
            cookie_file = Path(cookie_path)
            if cookie_file.exists():
                file_size = cookie_file.stat().st_size
                opts["cookiefile"] = str(cookie_file)
                logger.info(
                    f"[INFO_EXTRACTOR] Using cookie file: {cookie_path} (size: {file_size} bytes)"
                )
            else:
                logger.warning(
                    f"[INFO_EXTRACTOR] Cookie file does not exist: {cookie_path}"
                )
        elif browser:
            opts["cookiesfrombrowser"] = (browser,)
            logger.info(f"[INFO_EXTRACTOR] Using browser cookies: {browser}")

        # Set client type - default to Android for better compatibility with mobile cookies
        client_type = client or "android"
        opts["extractor_args"] = {"youtube": {"player_client": [client_type]}}
        logger.debug(
            f"[INFO_EXTRACTOR] Built options with client: {client_type}, cookie_file: {opts.get('cookiefile', 'None')}"
        )

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
