"""YouTube cookie management functionality."""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import platform


logger = logging.getLogger(__name__)


class YouTubeCookieManager:
    """Manages YouTube-specific cookie detection and integration."""

    def __init__(self, cookie_manager: Optional[ICookieManager] = None):
        self._cookie_manager = cookie_manager
        self._platform = self._detect_platform()

    def _detect_platform(self) -> PlatformType:
        """Detect the current platform."""
        system = platform.system().lower()
        if system == "windows":
            return PlatformType.WINDOWS
        elif system == "darwin":
            return PlatformType.MACOS
        elif system == "linux":
            return PlatformType.LINUX
        else:
            raise ValueError(f"Unsupported platform: {system}")

    def get_youtube_cookie_info(self) -> Optional[Dict[str, Any]]:
        """Get cookie information formatted for yt-dlp."""
        if not self._cookie_manager or not self._cookie_manager.has_valid_cookies():
            return None

        cookie_path = self._cookie_manager.get_current_cookie_path()
        if not cookie_path:
            return None

        # Return format compatible with yt-dlp
        if cookie_path.endswith('.txt'):
            return {'cookiefile': cookie_path}
        else:
            return {'cookies': cookie_path}

    def should_use_cookies(self, url: str) -> bool:
        """Check if cookies should be used for this URL."""
        return ('youtube.com' in url or 'youtu.be' in url) and self._cookie_manager

    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        if not self._cookie_manager:
            return None
        return self._cookie_manager.detect_cookies_for_browser(browser)