from __future__ import annotations

import re
import time

import yt_dlp

from src.core.enums.compat import StrEnum
from src.core.enums.download_error_type import DownloadErrorType
from src.core.interfaces import IErrorNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeErrorBucket(StrEnum):
    LOGIN_REQUIRED = "login_required"
    FORMAT = "format"
    NETWORK = "network"
    BROWSER_UNAVAILABLE = "browser_unavailable"
    KEYCHAIN = "keychain"
    OTHER = "other"


class YouTubeErrorHandler:
    """Handles YouTube-specific errors with bucketed classification and routing."""

    _RATE_LIMIT_PATTERN = re.compile(r"HTTP Error 429", re.IGNORECASE)
    _NETWORK_PATTERN = re.compile(
        r"(Connection refused|Network Error|Unable to download|Errno 111|timed? out)",
        re.IGNORECASE,
    )
    _FORMAT_PATTERN = re.compile(
        r"(Requested format is not available|No video formats found)",
        re.IGNORECASE,
    )

    _LOGIN_REQUIRED_INDICATORS = (
        "sign in to confirm",
        "login required",
        "authentication",
        "use --cookies",
        "age-restricted",
    )
    _BROWSER_UNAVAILABLE_INDICATORS = (
        "could not find firefox",
        "could not find chrome",
        "browser not found",
        "failed to load cookies from browser",
        "could not find cookies database",
    )
    _KEYCHAIN_INDICATORS = (
        "keyring",
        "keychain",
        "secretstorage",
        "failed to decrypt",
        "password store",
    )

    def __init__(self, error_handler: IErrorNotifier | None = None) -> None:
        self.error_handler = error_handler

    def classify_ytdlp_error(self, error_msg: str) -> YouTubeErrorBucket:
        """Classify yt-dlp error into stable fallback buckets."""
        lower_msg = error_msg.lower()

        match True:
            case _ if any(token in lower_msg for token in self._LOGIN_REQUIRED_INDICATORS):
                return YouTubeErrorBucket.LOGIN_REQUIRED
            case _ if any(token in lower_msg for token in self._BROWSER_UNAVAILABLE_INDICATORS):
                return YouTubeErrorBucket.BROWSER_UNAVAILABLE
            case _ if any(token in lower_msg for token in self._KEYCHAIN_INDICATORS):
                return YouTubeErrorBucket.KEYCHAIN
            case _ if self._NETWORK_PATTERN.search(error_msg):
                return YouTubeErrorBucket.NETWORK
            case _ if self._FORMAT_PATTERN.search(error_msg):
                return YouTubeErrorBucket.FORMAT
            case _:
                return YouTubeErrorBucket.OTHER

    def classify_error(self, error_msg: str) -> DownloadErrorType:
        """Classify into generic download error categories (backward compatible)."""
        bucket = self.classify_ytdlp_error(error_msg)

        match bucket:
            case YouTubeErrorBucket.NETWORK:
                return DownloadErrorType.NETWORK
            case YouTubeErrorBucket.FORMAT:
                return DownloadErrorType.FORMAT
            case _ if self._RATE_LIMIT_PATTERN.search(error_msg):
                return DownloadErrorType.RATE_LIMIT
            case _:
                return DownloadErrorType.OTHER

    def handle_rate_limit_error(self, attempt: int, retry_wait: int) -> bool:
        wait_time = retry_wait * (2**attempt)
        logger.warning(f"YouTube rate limit hit, waiting {wait_time} seconds before retry")
        time.sleep(wait_time)
        return True

    def handle_network_error(
        self,
        attempt: int,
        max_retries: int,
        retry_wait: int,
        error_msg: str,
    ) -> bool:
        if attempt >= max_retries - 1:
            logger.error(f"Failed to download after {max_retries} attempts: {error_msg}")
            return False

        wait_time = retry_wait * (attempt + 1)
        logger.warning(f"Network error, retry {attempt + 1}/{max_retries} in {wait_time}s")
        time.sleep(wait_time)
        return True

    def handle_format_error(
        self,
        attempt: int,
        opts: dict,
        url: str,
        quality_format_map: dict[str, str],
    ) -> bool:
        fallback_strategies = {
            0: (
                quality_format_map.get("best", "best"),
                f"Format not available ({opts.get('format', 'unknown')}), retrying with 'best'",
            ),
            1: (
                quality_format_map.get("lowest", "worst"),
                "Best format failed, trying 'worst' as fallback",
            ),
        }

        if not (strategy := fallback_strategies.get(attempt)):
            self._log_format_failure(opts, url)
            return False

        format_type, message = strategy
        logger.warning(message)
        opts["format"] = format_type
        return True

    def _log_format_failure(self, opts: dict, url: str) -> None:
        logger.error("All format attempts failed. This may be due to:")
        logger.error("  1. Outdated yt-dlp version (run: pip install -U yt-dlp)")
        logger.error("  2. YouTube access restrictions or region-locking")
        logger.error("  3. Need for browser cookies to access the video")

        try:
            logger.info("Attempting to list available formats...")
            list_opts = opts.copy()
            list_opts.pop("format", None)
            with yt_dlp.YoutubeDL(list_opts) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(url, download=False)
                if not (info and isinstance(info, dict) and "formats" in info):
                    return

                logger.info(f"Available formats for {url}:")
                formats = info.get("formats", [])
                if not isinstance(formats, list):
                    logger.warning("Formats is not a list")
                    return

                for fmt in formats[:10]:
                    logger.info(
                        f"  Format {fmt.get('format_id', 'unknown')}: "
                        f"{fmt.get('format_note', 'N/A')} - "
                        f"{fmt.get('ext', 'unknown')} - "
                        f"height={fmt.get('height', 'N/A')}"
                    )
        except Exception as list_err:
            logger.warning(f"Could not list formats: {list_err}")

    def log_specific_error(self, error_msg: str) -> None:
        error_messages = {
            "This video is unavailable": "This YouTube video is unavailable or private",
            "Video unavailable": "This YouTube video has been removed or is private",
            "Sign in to confirm your age": "This YouTube video requires age verification",
            "Only images are available": (
                "This YouTube video only has image storyboards available (no video/audio streams). "
                "The video may be processing, region-locked, or YouTube is blocking access."
            ),
            "nsig extraction failed": (
                "YouTube's anti-bot protection is blocking download. "
                "Try: 1) Update yt-dlp to latest version, 2) Use browser cookies, "
                "3) Wait and try again later"
            ),
        }

        for key, message in error_messages.items():
            if key in error_msg:
                logger.error(message)
                return

        logger.error(f"YouTube download error: {error_msg}")
