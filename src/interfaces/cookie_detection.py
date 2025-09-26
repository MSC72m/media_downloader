"""Interface for cookie detection functionality."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum
import platform


class BrowserType(Enum):
    """Supported browser types for cookie detection."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    SAFARI = "safari"


class PlatformType(Enum):
    """Supported platforms."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"


class ICookieDetector(ABC):
    """Interface for detecting browser cookies."""

    @abstractmethod
    def detect_cookies(self, browser: BrowserType) -> Optional[str]:
        """
        Detect cookies for the specified browser.

        Args:
            browser: Browser type to detect cookies for

        Returns:
            Path to cookie file if found, None otherwise
        """
        pass

    @abstractmethod
    def get_supported_browsers(self) -> List[BrowserType]:
        """Get list of browsers supported on current platform."""
        pass

    @abstractmethod
    def validate_cookie_file(self, cookie_path: str) -> bool:
        """Validate that a cookie file exists and contains data."""
        pass


class ICookieManager(ABC):
    """Interface for managing cookie detection and integration."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the cookie manager."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    def detect_platform(self) -> PlatformType:
        """Detect the current platform."""
        pass

    @abstractmethod
    def get_available_browsers(self) -> List[BrowserType]:
        """Get list of browsers available on current platform."""
        pass

    @abstractmethod
    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        pass

    @abstractmethod
    def set_youtube_cookies(self, cookie_path: str) -> None:
        """Set cookies for YouTube downloads."""
        pass

    @abstractmethod
    def has_valid_cookies(self) -> bool:
        """Check if valid cookies are currently set."""
        pass

    @abstractmethod
    def get_current_cookie_path(self) -> Optional[str]:
        """Get the current cookie path."""
        pass