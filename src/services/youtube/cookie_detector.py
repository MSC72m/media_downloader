"""Service for detecting browser cookies across platforms."""

import os
from src.utils.logger import get_logger
from pathlib import Path
from typing import Optional, List, Dict, Any
import platform
import sqlite3
import shutil
import tempfile

from ...interfaces.cookie_detection import ICookieDetector, ICookieManager, BrowserType, PlatformType

logger = get_logger(__name__)


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
        """Detect Chrome cookies and convert to Netscape format."""
        paths = self._browser_paths[BrowserType.CHROME]

        # Find Chrome cookies database
        cookie_db = None

        # Check default profile first
        default_path = paths["default"]
        if default_path.exists() and self.validate_cookie_file(str(default_path)):
            cookie_db = str(default_path)
        else:
            # Check other profiles
            profile_pattern = paths["profile"]
            base_dir = profile_pattern.parent

            for profile_dir in base_dir.glob("Profile *"):
                cookie_path = profile_dir / "Cookies"
                if cookie_path.exists() and self.validate_cookie_file(str(cookie_path)):
                    cookie_db = str(cookie_path)
                    break

        if not cookie_db:
            logger.info("Chrome cookies database not found")
            return None

        # Convert Chrome cookies to Netscape format
        return self._convert_chrome_cookies(cookie_db)

    def _convert_chrome_cookies(self, chrome_db_path: str) -> Optional[str]:
        """Convert Chrome SQLite cookies to Netscape format."""
        try:
            # Create temporary file for Netscape format cookies
            temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
            temp_path = temp_file.name

            # Create a temporary copy of the database to avoid locking issues
            temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            temp_db.close()

            try:
                shutil.copy2(chrome_db_path, temp_db.name)

                # Connect to Chrome cookies database
                conn = sqlite3.connect(temp_db.name)
                cursor = conn.cursor()

                # Check if cookies are encrypted (modern macOS Chrome)
                cursor.execute("PRAGMA table_info(cookies)")
                columns = [row[1] for row in cursor.fetchall()]

                # If encrypted_value column exists, cookies are encrypted
                if 'encrypted_value' in columns:
                    logger.warning("Chrome cookies are encrypted. On macOS, cookies may not be accessible due to system encryption.")
                    # Try to get any unencrypted cookies first
                    cursor.execute("""
                        SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                        FROM cookies
                        WHERE (host_key LIKE '%.youtube.com' OR host_key LIKE '%.google.com')
                        AND value IS NOT NULL AND value != ''
                        ORDER BY creation_utc DESC
                    """)
                else:
                    # Older Chrome without encryption
                    cursor.execute("""
                        SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
                        FROM cookies
                        WHERE host_key LIKE '%.youtube.com' OR host_key LIKE '%.google.com'
                        ORDER BY creation_utc DESC
                    """)

                # Write Netscape format header
                temp_file.write("# Netscape HTTP Cookie File\n")
                temp_file.write("# This is a generated file! Do not edit.\n\n")

                cookie_count = 0
                for name, value, host_key, path, expires_utc, is_secure, is_httponly in cursor.fetchall():
                    # Skip cookies without names or values
                    if not name:
                        continue

                    # For encrypted cookies, the value might be empty but we should include the name
                    # with a placeholder value to indicate the cookie exists but is encrypted
                    if not value:
                        value = "encrypted"
                        logger.info(f"Cookie '{name}' appears to be encrypted, using placeholder")

                    # Convert Chrome expires_utc to Unix timestamp
                    # Chrome uses Windows epoch (1601-01-01) in microseconds
                    if expires_utc:
                        # Convert to Unix timestamp (seconds since 1970-01-01)
                        unix_timestamp = (expires_utc - 11644473600000000) // 1000000
                    else:
                        unix_timestamp = 0

                    # Netscape format: host, include_subdomains, path, is_secure, expires, name, value
                    domain_flag = "TRUE" if host_key.startswith(".") else "FALSE"
                    secure_flag = "TRUE" if is_secure else "FALSE"
                    # httponly_flag = "FALSE" if is_httponly else "TRUE"  # Inverted for Netscape format

                    line = f"{host_key}\t{domain_flag}\t{path}\t{secure_flag}\t{unix_timestamp}\t{name}\t{value}\n"
                    temp_file.write(line)
                    cookie_count += 1

                conn.close()
                temp_file.close()

                if cookie_count > 0:
                    logger.info(f"Extracted {cookie_count} YouTube/Google cookies from Chrome")
                    return temp_path
                else:
                    logger.info("No YouTube/Google cookies found in Chrome")
                    os.unlink(temp_path)
                    return None

            except Exception as e:
                logger.error(f"Error reading Chrome cookies database: {e}")
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return None
            finally:
                # Clean up temporary database
                try:
                    os.unlink(temp_db.name)
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Error converting Chrome cookies: {e}")
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
                    return bool(content and (not content.startswith('#') or len(content.split('\n')) > 2))
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
            try:
                # Check if browser cookie database exists without full detection
                if self._detector._browser_paths.get(browser):
                    # Quick check for browser installation
                    if self._quick_browser_check(browser):
                        available.append(browser)
            except Exception as e:
                logger.debug(f"Error checking browser {browser.value}: {e}")
                continue

        return available

    def _quick_browser_check(self, browser: BrowserType) -> bool:
        """Quick check if browser is installed without full cookie detection."""
        try:
            paths = self._detector._browser_paths.get(browser, {})
            if not paths:
                return False

            if browser == BrowserType.CHROME:
                # Check if Chrome directory exists
                chrome_paths = paths
                default_path = chrome_paths.get("default")
                if default_path and default_path.parent.exists():
                    return True
            elif browser == BrowserType.FIREFOX:
                # Check if Firefox profiles directory exists
                firefox_paths = paths
                profiles_path = firefox_paths.get("profiles")
                if profiles_path and profiles_path.parent.exists():
                    return True
            elif browser == BrowserType.SAFARI:
                # Check if Safari cookies file exists
                safari_paths = paths
                cookies_path = safari_paths.get("cookies")
                if cookies_path and cookies_path.parent.exists():
                    return True

            return False
        except Exception as e:
            logger.debug(f"Error in quick browser check for {browser.value}: {e}")
            return False

    def detect_cookies_for_browser(self, browser: BrowserType) -> Optional[str]:
        """Detect cookies for a specific browser."""
        cookie_path = self._detector.detect_cookies(browser)
        if cookie_path:
            self._current_cookie_path = cookie_path
            logger.info(f"Detected cookies for {browser.value}: {cookie_path}")
        return cookie_path

    def set_youtube_cookies(self, cookie_path: str) -> None:
        """Set cookies for YouTube downloads."""
        if not cookie_path:
            logger.error("Empty cookie path provided")
            raise ValueError("Cookie path cannot be empty")
            
        if not os.path.exists(cookie_path):
            logger.error(f"Cookie file does not exist: {cookie_path}")
            raise ValueError(f"Cookie file does not exist: {cookie_path}")

        try:
            if not self._detector.validate_cookie_file(cookie_path):
                logger.error(f"Invalid cookie file format: {cookie_path}")
                raise ValueError(f"Invalid cookie file: {cookie_path}")
                
            self._current_cookie_path = cookie_path
            logger.info(f"Successfully set YouTube cookies from: {cookie_path}")
        except Exception as e:
            logger.error(f"Error validating cookie file: {str(e)}")
            raise ValueError(f"Error processing cookie file: {str(e)}")

    def has_valid_cookies(self) -> bool:
        """Check if valid cookies are currently set."""
        if not self._current_cookie_path:
            logger.debug("No cookie path is currently set")
            return False
            
        if not os.path.exists(self._current_cookie_path):
            logger.warning(f"Cookie file no longer exists: {self._current_cookie_path}")
            return False
            
        try:
            is_valid = self._detector.validate_cookie_file(self._current_cookie_path)
            if not is_valid:
                logger.warning(f"Cookie file is invalid: {self._current_cookie_path}")
            return is_valid
        except Exception as e:
            logger.error(f"Error validating cookie file: {str(e)}")
            return False

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
