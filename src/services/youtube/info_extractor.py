from pathlib import Path
from typing import Any, cast

import requests
import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Browsers to try for --cookies-from-browser, in priority order
_BROWSER_CANDIDATES = ["chrome", "firefox", "edge", "chromium", "brave", "opera", "safari"]


class YouTubeInfoExtractor:
    """Extracts YouTube video information using yt-dlp library.

    Extraction strategy (in order):
    1. Cookie file with multiple clients
    2. No cookies with multiple clients
    3. Browser cookies as a late fallback
    """

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        self.error_handler = error_handler
        self.config = config

    def extract_info(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract video information using yt-dlp library.

        Args:
            url: YouTube URL
            cookie_path: Path to cookie file
            browser: Browser name for cookie extraction

        Returns:
            Video info dict or None if extraction fails
        """
        # Strategy 1: Try cookie file first when explicitly provided.
        # Auto-generated cookies can fail, but when they work they are the best signal.
        if cookie_path:
            info = self._try_cookie_file(url, cookie_path)
            if info:
                return info

        # Strategy 2: Try no-cookies for public videos.
        info = self._try_no_cookies(url)
        if info:
            return info

        # Strategy 3: Browser cookies as a late fallback.
        info = self._try_browser_cookies(url, browser)
        if info:
            return info

        fallback = self._fetch_oembed_fallback(url)
        if fallback:
            logger.warning(
                "[INFO_EXTRACTOR] Falling back to oEmbed metadata after yt-dlp extraction failure"
            )
            return fallback

        logger.error("[INFO_EXTRACTOR] All extraction strategies exhausted")
        return None

    # ── Strategy helpers ─────────────────────────────────────────────

    def _try_browser_cookies(
        self, url: str, preferred_browser: str | None = None
    ) -> dict[str, Any] | None:
        """Try extracting with browser cookies.

        Uses 'web' client first (matches the desktop browser cookies),
        then falls back to other clients if format issues arise.
        """
        browsers = self._get_browser_list(preferred_browser)

        for browser_name in browsers:
            for client in ["default"]:
                info = self._extract_single(
                    url,
                    browser=browser_name,
                    client=client,
                    label=f"browser({browser_name})+{client}",
                )
                if info:
                    return info

        return None

    def _try_cookie_file(self, url: str, cookie_path: str) -> dict[str, Any] | None:
        """Try extracting with a cookie file, cycling through client types."""
        if not self._validate_cookie_file(cookie_path):
            return None

        # Web client first, then mobile/embedded clients
        clients = ["web", "default"]
        for client in clients:
            info = self._extract_single(
                url,
                cookie_path=cookie_path,
                client=client,
                label=f"cookiefile+{client}",
            )
            if info:
                return info

        return None

    def _try_no_cookies(self, url: str) -> dict[str, Any] | None:
        """Last-resort extraction without any cookies."""
        clients = ["web", "default"]
        for client in clients:
            info = self._extract_single(
                url,
                client=client,
                label=f"nocookies+{client}",
            )
            if info:
                return info
        return None

    # ── Core extraction ──────────────────────────────────────────────

    def _extract_single(
        self,
        url: str,
        cookie_path: str | None = None,
        browser: str | None = None,
        client: str = "web",
        label: str = "",
    ) -> dict[str, Any] | None:
        """Run a single yt-dlp extraction attempt.

        Returns the info dict on success, or None on failure.
        """
        opts = self._build_options(
            cookie_path=cookie_path,
            browser=browser,
            client=client,
        )
        logger.info(f"[INFO_EXTRACTOR] Trying extraction: {label}")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                raw_info = ydl.extract_info(url, download=False)
                if raw_info:
                    logger.info(f"[INFO_EXTRACTOR] Success with: {label}")
                    return cast(dict[str, Any], raw_info)
        except yt_dlp.utils.DownloadError as e:  # type: ignore[attr-defined]
            error_msg = str(e)
            short = error_msg[:200]

            if self._is_format_error(error_msg) and client != "default":
                # Format mismatch - retry same auth but without client override
                logger.warning(
                    f"[INFO_EXTRACTOR] Format error with {label}, retrying without client override: {short}"
                )
                return self._retry_without_client(url, cookie_path, browser, label)

            if self._is_cookie_error(error_msg):
                logger.warning(f"[INFO_EXTRACTOR] Auth/cookie error with {label}: {short}")
            else:
                logger.warning(f"[INFO_EXTRACTOR] Download error with {label}: {short}")
        except Exception as e:
            logger.warning(
                f"[INFO_EXTRACTOR] Unexpected error with {label}: {e}",
                exc_info=True,
            )

        return None

    def _retry_without_client(
        self,
        url: str,
        cookie_path: str | None,
        browser: str | None,
        label: str,
    ) -> dict[str, Any] | None:
        """Retry extraction without player_client override (uses yt-dlp defaults)."""
        opts = self._build_options(
            cookie_path=cookie_path,
            browser=browser,
            client=None,  # let yt-dlp pick
        )
        retry_label = f"{label}(no-client-override)"
        logger.info(f"[INFO_EXTRACTOR] Retrying: {retry_label}")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                raw_info = ydl.extract_info(url, download=False)
                if raw_info:
                    logger.info(f"[INFO_EXTRACTOR] Success with: {retry_label}")
                    return cast(dict[str, Any], raw_info)
        except Exception as e:
            logger.debug(f"[INFO_EXTRACTOR] Retry failed ({retry_label}): {e}")

        return None

    # ── Option builder ───────────────────────────────────────────────

    def _build_options(
        self,
        cookie_path: str | None = None,
        browser: str | None = None,
        client: str | None = None,
    ) -> dict[str, Any]:
        """Build yt-dlp options for metadata extraction.

        Args:
            cookie_path: Path to Netscape cookie file
            browser: Browser name for --cookies-from-browser
            client: YouTube player client type, or None for yt-dlp default
        """
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extract_flat": False,
            "skip_download": True,
            "ignoreconfig": True,
            "nocheckcertificate": True,
            "socket_timeout": 15,
        }

        # Auth source
        if cookie_path:
            cookie_file = Path(cookie_path)
            if cookie_file.exists() and cookie_file.stat().st_size > 0:
                opts["cookiefile"] = str(cookie_file)
                logger.debug(
                    f"[INFO_EXTRACTOR] Cookie file: {cookie_path} "
                    f"({cookie_file.stat().st_size} bytes)"
                )
        elif browser:
            opts["cookiesfrombrowser"] = (browser,)
            logger.debug(f"[INFO_EXTRACTOR] Browser cookies: {browser}")

        # Player client
        if client and client != "default":
            opts["extractor_args"] = {"youtube": {"player_client": [client]}}

        return opts

    # ── Helpers ───────────────────────────────────────────────────────

    def _get_browser_list(self, preferred: str | None = None) -> list[str]:
        """Return ordered list of browsers to try."""
        if preferred:
            return [preferred]
        # Keep this short to avoid long chains of predictable "browser not found" failures.
        return ["chrome"]

    @staticmethod
    def _validate_cookie_file(cookie_path: str) -> bool:
        """Check that a cookie file exists and is non-empty."""
        cookie_file = Path(cookie_path)
        if not cookie_file.exists():
            logger.warning(f"[INFO_EXTRACTOR] Cookie file not found: {cookie_path}")
            return False
        if cookie_file.stat().st_size == 0:
            logger.warning(f"[INFO_EXTRACTOR] Cookie file is empty: {cookie_path}")
            return False
        return True

    @staticmethod
    def _is_cookie_error(error_msg: str) -> bool:
        """Check if the error indicates an authentication / cookie problem."""
        indicators = [
            "sign in to confirm",
            "bot",
            "use --cookies",
            "authentication",
            "unauthorized",
            "login required",
        ]
        lower = error_msg.lower()
        return any(ind in lower for ind in indicators)

    @staticmethod
    def _is_format_error(error_msg: str) -> bool:
        """Check if the error is about format availability."""
        indicators = [
            "requested format is not available",
            "no video formats found",
            "format is not available",
        ]
        lower = error_msg.lower()
        return any(ind in lower for ind in indicators)

    def _fetch_oembed_fallback(self, url: str) -> dict[str, Any] | None:
        """Fetch minimal metadata from YouTube oEmbed endpoint."""
        try:
            response = requests.get(
                "https://www.youtube.com/oembed",
                params={"url": url, "format": "json"},
                timeout=self.config.network.default_timeout,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            return {
                "title": data.get("title", ""),
                "uploader": data.get("author_name", ""),
                "channel": data.get("author_name", ""),
                "thumbnail": data.get("thumbnail_url", ""),
                "duration": 0,
                "view_count": 0,
                "formats": [],
            }
        except Exception:
            return None
