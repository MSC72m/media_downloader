"""Handler for cookie detection and integration with the application."""

from src.core.config import AppConfig
from src.core.interfaces import ICookieHandler, ICookieManager
from src.handlers.service_detector import ServiceDetector
from src.services.youtube.cookie_detector import CookieManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CookieHandler(ICookieHandler):
    def __init__(self, config: AppConfig, cookie_manager: ICookieManager | None = None):
        self.config = config
        self._cookie_manager = cookie_manager or CookieManager()
        self._service_detector = ServiceDetector()
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        self._cookie_manager.initialize()
        self._initialized = True
        logger.info("Cookie handler initialized")

    def cleanup(self) -> None:
        if not self._initialized:
            return

        self._cookie_manager.cleanup()
        self._initialized = False

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

    def get_current_cookie_path(self) -> str | None:
        """Get the current cookie path."""
        return self._cookie_manager.get_current_cookie_path()

    def should_show_cookie_option(self, url: str) -> bool:
        """Check if cookie option should be shown for this URL."""
        service_type = self._service_detector.detect_service(url)
        return service_type and service_type.value == "youtube"

    def get_cookie_info_for_ytdlp(self) -> dict | None:
        """Get cookie information for yt-dlp integration."""
        return self._cookie_manager.get_cookie_info_for_ytdlp()
