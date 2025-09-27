"""Handler for cookie detection and integration with the application."""

import logging
from typing import Optional, Callable, Any
from src.core.models import ServiceType
from src.services.youtube.cookie_detector import CookieManager
from src.interfaces.cookie_detection import BrowserType, PlatformType, ICookieManager
from src.handlers.service_detector import ServiceDetector

logger = logging.getLogger(__name__)


class CookieHandler:
    """Handler for cookie detection and integration."""

    def __init__(self, cookie_manager: Optional[ICookieManager] = None):
        self._cookie_manager = cookie_manager or CookieManager()
        self._service_detector = ServiceDetector()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the cookie handler."""
        if self._initialized:
            return

        self._cookie_manager.initialize()
        self._initialized = True
        logger.info("Cookie handler initialized")

    def cleanup(self) -> None:
        """Clean up resources."""
        if not self._initialized:
            return

        self._cookie_manager.cleanup()
        self._initialized = False

    def get_platform(self) -> PlatformType:
        """Get the current platform."""
        return self._cookie_manager.detect_platform()

    def get_supported_browsers(self) -> list[BrowserType]:
        """Get list of browsers supported on current platform."""
        return self._cookie_manager.get_available_browsers()

    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        return self._cookie_manager.detect_cookies_for_browser(browser)

    def set_cookie_file(self, cookie_path: str) -> bool:
        """Set cookie file from user selection."""
        try:
            self._cookie_manager.set_youtube_cookies(cookie_path)
            return True
        except Exception as e:
            logger.error(f"Error setting cookie file: {e}")
            return False

    def has_valid_cookies(self) -> bool:
        """Check if valid cookies are currently set."""
        return self._cookie_manager.has_valid_cookies()

    def get_current_cookie_path(self) -> Optional[str]:
        """Get the current cookie path."""
        return self._cookie_manager.get_current_cookie_path()

    def should_show_cookie_option(self, url: str) -> bool:
        """Check if cookie option should be shown for this URL."""
        service_type = self._service_detector.detect_service(url)
        return service_type and service_type.value == "youtube"

    def get_cookie_info_for_ytdlp(self) -> Optional[dict]:
        """Get cookie information for yt-dlp integration."""
        return self._cookie_manager.get_cookie_info_for_ytdlp()