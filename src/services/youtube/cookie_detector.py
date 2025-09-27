"""Service for detecting browser cookies across platforms."""

import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import platform
import sqlite3
import shutil
import tempfile

from ...interfaces.cookie_detection import ICookieDetector, ICookieManager, BrowserType, PlatformType

logger = logging.getLogger(__name__)


class CookieDetector(ICookieDetector):
    """Concrete implementation for detecting browser cookies."""

    def __init__(self):
        self._platform = self._detect_platform()
        self._browser_paths = self._get_browser_paths()

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

    def _get_browser_paths(self) -> Dict[BrowserType, Dict[str, Any]]:
        """Get browser cookie paths for current platform."""
        paths = {}

        # Chrome paths
        if self._platform == PlatformType.WINDOWS:
            chrome_base = Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data"
            chrome_paths = {
                "default": chrome_base / "Default" / "Cookies",
                "profile": chrome_base / "Profile *" / "Cookies"
            }
        elif self._platform == PlatformType.MACOS:
            chrome_base = Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
            chrome_paths = {
                "default": chrome_base / "Default" / "Cookies",
                "profile": chrome_base / "Profile *" / "Cookies"
            }
        else:  # Linux
            chrome_base = Path.home() / ".config" / "google-chrome"
            chrome_paths = {
                "default": chrome_base / "Default" / "Cookies",
                "profile": chrome_base / "Profile *" / "Cookies"
            }
        paths[BrowserType.CHROME] = chrome_paths

        # Firefox paths
        if self._platform == PlatformType.WINDOWS:
            firefox_base = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"
        elif self._platform == PlatformType.MACOS:
            firefox_base = Path.home() / "Library" / "Application Support" / "Firefox" / "Profiles"
        else:  # Linux
            firefox_base = Path.home() / ".mozilla" / "firefox"
        paths[BrowserType.FIREFOX] = {"profiles": firefox_base / "*.default*"}

        # Safari paths (macOS only)
        if self._platform == PlatformType.MACOS:
            safari_path = Path.home() / "Library" / "Cookies" / "Cookies.binarycookies"
            paths[BrowserType.SAFARI] = {"cookies": safari_path}

        return paths

    def detect_cookies(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for the specified browser."""
        if browser not in self._browser_paths:
            logger.warning(f"Browser {browser.value} not supported on {self._platform.value}")
            return None

        try:
            if browser == BrowserType.CHROME:
                return self._detect_chrome_cookies()
            elif browser == BrowserType.FIREFOX:
                return self._detect_firefox_cookies()
            elif browser == BrowserType.SAFARI:
                return self._detect_safari_cookies()
        except Exception as e:
            logger.error(f"Error detecting cookies for {browser.value}: {e}")
            return None

        return None

    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        return self.detect_cookies(browser)

    def get_current_cookie_path(self) -> Optional[str]:
        """Get the current cookie path."""
        return None

    def _detect_chrome_cookies(self) -> Optional[str]:
        """Detect Chrome cookies."""
        paths = self._browser_paths[BrowserType.CHROME]

        # Check default profile first
        default_path = paths["default"]
        if default_path.exists() and self.validate_cookie_file(str(default_path)):
            return str(default_path)

        # Check other profiles
        profile_pattern = paths["profile"]
        base_dir = profile_pattern.parent
        profile_pattern_str = profile_pattern.name

        for profile_dir in base_dir.glob("Profile *"):
            cookie_path = profile_dir / "Cookies"
            if cookie_path.exists() and self.validate_cookie_file(str(cookie_path)):
                return str(cookie_path)

        return None

    def _detect_firefox_cookies(self) -> Optional[str]:
        """Detect Firefox cookies and create compatible file."""
        paths = self._browser_paths[BrowserType.FIREFOX]
        profile_pattern = paths["profiles"]

        # Find Firefox profile directories
        profile_dirs = list(profile_pattern.parent.glob(profile_pattern.name))
        if not profile_dirs:
            return None

        # Use the first profile found
        profile_dir = profile_dirs[0]
        cookies_db = profile_dir / "cookies.sqlite"

        if not cookies_db.exists():
            return None

        # Firefox uses SQLite format, need to convert to Netscape format for yt-dlp
        return self._convert_firefox_cookies(str(cookies_db))

    def _detect_safari_cookies(self) -> Optional[str]:
        """Detect Safari cookies and create compatible file."""
        paths = self._browser_paths[BrowserType.SAFARI]
        cookie_path = paths["cookies"]

        if not cookie_path.exists():
            return None

        # Safari uses binary format, need to convert to Netscape format
        return self._convert_safari_cookies(str(cookie_path))

    def _convert_firefox_cookies(self, firefox_db_path: str) -> Optional[str]:
        """Convert Firefox SQLite cookies to Netscape format."""
        try:
            # Create temporary file for Netscape format cookies
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            temp_path = temp_file.name

            # Connect to Firefox cookies database
            conn = sqlite3.connect(firefox_db_path)
            cursor = conn.cursor()

            # Query cookies
            cursor.execute("""
                SELECT host, name, value, path, expiry, isSecure, isHttpOnly
                FROM moz_cookies
                WHERE host LIKE '%youtube%' OR host LIKE '%google%'
            """)

            # Write Netscape format
            temp_file.write("# Netscape HTTP Cookie File\n")
            temp_file.write("# This is a generated file! Do not edit.\n\n")

            for host, name, value, path, expiry, is_secure, is_http_only in cursor.fetchall():
                # Netscape format: domain, include_subdomains, path, is_secure, expires, name, value
                domain_flag = "TRUE" if host.startswith(".") else "FALSE"
                secure_flag = "TRUE" if is_secure else "FALSE"

                # Skip cookies without names or values
                if not name or not value:
                    continue

                line = f"{host}\t{domain_flag}\t{path}\t{secure_flag}\t{expiry or 0}\t{name}\t{value}\n"
                temp_file.write(line)

            conn.close()
            temp_file.close()

            return temp_path

        except Exception as e:
            logger.error(f"Error converting Firefox cookies: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None

    def _convert_safari_cookies(self, safari_db_path: str) -> Optional[str]:
        """Convert Safari binary cookies to Netscape format."""
        # Safari cookie conversion is complex and requires external tools
        # For now, we'll return None and let the user handle it manually
        logger.warning("Safari cookie conversion requires manual intervention")
        return None

    def get_supported_browsers(self) -> List[BrowserType]:
        """Get list of browsers supported on current platform."""
        supported = [BrowserType.CHROME, BrowserType.FIREFOX]

        if self._platform == PlatformType.MACOS:
            supported.append(BrowserType.SAFARI)

        return supported

    def validate_cookie_file(self, cookie_path: str) -> bool:
        """Validate that a cookie file exists and contains data."""
        if not os.path.exists(cookie_path):
            return False

        try:
            if cookie_path.endswith('.sqlite'):
                # Check if it's a valid SQLite database
                conn = sqlite3.connect(cookie_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                conn.close()
                return 'cookies' in tables
            elif cookie_path.endswith('.txt'):
                # Check if Netscape format file has content
                with open(cookie_path, 'r') as f:
                    content = f.read().strip()
                    return content and not content.startswith('#') or len(content.split('\n')) > 2
            else:
                # Check file size (Chrome cookies database)
                return os.path.getsize(cookie_path) > 0
        except Exception as e:
            logger.error(f"Error validating cookie file {cookie_path}: {e}")
            return False


class CookieManager(ICookieManager):
    """Manager for cookie detection and integration."""

    def __init__(self):
        self._detector = CookieDetector()
        self._current_cookie_path: Optional[str] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the cookie manager."""
        if self._initialized:
            return

        self._initialized = True
        logger.info("Cookie manager initialized")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._current_cookie_path and self._current_cookie_path.endswith('.txt'):
            # Clean up temporary cookie files
            try:
                os.unlink(self._current_cookie_path)
            except Exception as e:
                logger.warning(f"Error cleaning up cookie file: {e}")

        self._current_cookie_path = None
        self._initialized = False

    def detect_platform(self) -> PlatformType:
        """Detect the current platform."""
        return self._detector._platform

    def get_available_browsers(self) -> List[BrowserType]:
        """Get list of browsers available on current platform."""
        supported = self._detector.get_supported_browsers()
        available = []

        for browser in supported:
            if self._detector.detect_cookies(browser):
                available.append(browser)

        return available

    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        cookie_path = self._detector.detect_cookies(browser)
        if cookie_path:
            self._current_cookie_path = cookie_path
            logger.info(f"Detected cookies for {browser.value}: {cookie_path}")
        return cookie_path

    def set_youtube_cookies(self, cookie_path: str) -> None:
        """Set cookies for YouTube downloads."""
        if not os.path.exists(cookie_path):
            raise ValueError(f"Cookie file does not exist: {cookie_path}")

        if not self._detector.validate_cookie_file(cookie_path):
            raise ValueError(f"Invalid cookie file: {cookie_path}")

        self._current_cookie_path = cookie_path
        logger.info(f"Set YouTube cookies from: {cookie_path}")

    def has_valid_cookies(self) -> bool:
        """Check if valid cookies are currently set."""
        return bool(self._current_cookie_path and
                   os.path.exists(self._current_cookie_path) and
                   self._detector.validate_cookie_file(self._current_cookie_path))

    def get_current_cookie_path(self) -> Optional[str]:
        """Get the current cookie path."""
        return self._current_cookie_path

    def get_cookie_info_for_ytdlp(self) -> Optional[Dict[str, Any]]:
        """Get cookie information for yt-dlp integration."""
        if not self.has_valid_cookies():
            return None

        cookie_path = self.get_current_cookie_path()
        if not cookie_path:
            return None

        # Return format compatible with yt-dlp
        if cookie_path.endswith('.txt'):
            return {'cookiefile': cookie_path}
        else:
            return {'cookies': cookie_path}

    def get_youtube_cookie_info(self) -> Optional[Dict[str, Any]]:
        """Get YouTube cookie information for yt-dlp integration."""
        return self.get_cookie_info_for_ytdlp()