import os
from pathlib import Path

from src.core.config import AppConfig
from src.core.interfaces import ICookieHandler
from src.handlers.service_detector import ServiceDetector
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CookieHandler(ICookieHandler):
    """Simple cookie handler for manual cookie file selection.

    Note: Browser cookie detection has been removed. Cookies are now obtained via:
    - Auto-generation (AutoCookieManager with Playwright)
    - yt-dlp's --cookies-from-browser flag
    - Manual cookie file selection (this handler)
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self._service_detector = ServiceDetector()
        self._current_cookie_path: str | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the cookie handler."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("Cookie handler initialized")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._current_cookie_path = None
        self._initialized = False

    def set_cookie_file(self, cookie_path: str) -> bool:
        """Set cookie file from user selection.

        Args:
            cookie_path: Path to cookie file (Netscape format .txt file)

        Returns:
            True if cookie file was set successfully, False otherwise
        """
        if not cookie_path:
            logger.error("Empty cookie path provided")
            return False

        cookie_path_obj = Path(cookie_path)
        if not cookie_path_obj.exists():
            logger.error(f"Cookie file does not exist: {cookie_path}")
            return False

        if cookie_path_obj.suffix.lower() != ".txt":
            logger.warning(f"Cookie file should be .txt format (Netscape format): {cookie_path}")

        try:
            with open(cookie_path_obj, encoding="utf-8") as f:
                first_line = f.readline()
                if "# Netscape HTTP Cookie File" not in first_line and first_line.strip():
                    logger.warning(f"Cookie file may not be in Netscape format: {cookie_path}")
        except Exception as e:
            logger.error(f"Error reading cookie file: {e}")
            return False

        self._current_cookie_path = str(cookie_path_obj.absolute())
        logger.info(f"Successfully set cookie file: {self._current_cookie_path}")
        return True

    def has_valid_cookies(self) -> bool:
        """Check if valid cookies are currently set."""
        if not self._current_cookie_path:
            return False

        if not os.path.exists(self._current_cookie_path):
            logger.warning(f"Cookie file no longer exists: {self._current_cookie_path}")
            self._current_cookie_path = None
            return False

        return True

    def get_current_cookie_path(self) -> str | None:
        """Get the current cookie path."""
        return self._current_cookie_path if self.has_valid_cookies() else None

    def should_show_cookie_option(self, url: str) -> bool:
        """Check if cookie option should be shown for this URL."""
        service_type = self._service_detector.detect_service(url)
        return service_type and service_type.value == "youtube"

    def get_cookie_info_for_ytdlp(self) -> dict | None:
        """Get cookie information for yt-dlp integration."""
        cookie_path = self.get_current_cookie_path()
        if not cookie_path:
            return None

        return {"cookiefile": cookie_path}
