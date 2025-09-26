"""Cookie detection interfaces and types."""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Optional, Dict, Any, List


class BrowserType(StrEnum):
    """Browser type enumeration."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"


class PlatformType(StrEnum):
    """Platform type enumeration."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class ICookieDetector(ABC):
    """Interface for cookie detection functionality."""

    @abstractmethod
    def get_supported_browsers(self) -> List[BrowserType]:
        """Get list of supported browsers."""
        pass

    @abstractmethod
    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        pass

    @abstractmethod
    def get_current_cookie_path(self) -> Optional[str]:
        """Get the current cookie path."""
        pass


class ICookieManager(ABC):
    """Interface for cookie management functionality."""

    @abstractmethod
    def get_cookie_info_for_ytdlp(self) -> Optional[Dict[str, Any]]:
        """Get cookie information for yt-dlp."""
        pass

    @abstractmethod
    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        pass

    @abstractmethod
    def get_current_cookie_path(self) -> Optional[str]:
        """Get the current cookie path."""
        pass