"""YouTube-specific error handling - extracted for SOLID principles."""

import re
import time

import yt_dlp

from src.core.enums.download_error_type import DownloadErrorType
from src.core.interfaces import IErrorNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeErrorHandler:
    """Handles YouTube-specific download errors with classification and recovery strategies."""

    # Compiled regex patterns for efficient error classification
    _RATE_LIMIT_PATTERN = re.compile(r"HTTP Error 429", re.IGNORECASE)
    _NETWORK_PATTERN = re.compile(
        r"(Connection refused|Network Error|Unable to download|Errno 111)",
        re.IGNORECASE,
    )
    _FORMAT_PATTERN = re.compile(
        r"(Requested format is not available|No video formats found)", re.IGNORECASE
    )

    def __init__(self, error_handler: IErrorNotifier | None = None):
        """Initialize YouTube error handler.

        Args:
            error_handler: Optional general error handler for UI notifications
        """
        self.error_handler = error_handler

    def classify_error(self, error_msg: str) -> DownloadErrorType:
        """Classify the type of download error using pattern matching.

        Args:
            error_msg: Error message to classify

        Returns:
            DownloadErrorType enum value
        """
        if self._RATE_LIMIT_PATTERN.search(error_msg):
            return DownloadErrorType.RATE_LIMIT
        if self._NETWORK_PATTERN.search(error_msg):
            return DownloadErrorType.NETWORK
        if self._FORMAT_PATTERN.search(error_msg):
            return DownloadErrorType.FORMAT

        return DownloadErrorType.OTHER

    def handle_rate_limit_error(self, attempt: int, retry_wait: int) -> bool:
        """Handle rate limit error with exponential backoff.

        Args:
            attempt: Current attempt number (0-indexed)
            retry_wait: Base wait time in seconds

        Returns:
            True to continue retrying
        """
        wait_time = retry_wait * (2**attempt)
        logger.warning(f"YouTube rate limit hit, waiting {wait_time} seconds before retry")
        time.sleep(wait_time)
        return True

    def handle_network_error(
        self, attempt: int, max_retries: int, retry_wait: int, error_msg: str
    ) -> bool:
        """Handle network error with linear backoff.

        Args:
            attempt: Current attempt number (0-indexed)
            max_retries: Maximum number of retries
            retry_wait: Base wait time in seconds
            error_msg: Error message for logging

        Returns:
            True to continue retrying, False if max retries reached
        """
        if attempt >= max_retries - 1:
            logger.error(f"Failed to download after {max_retries} attempts: {error_msg}")
            return False

        wait_time = retry_wait * (attempt + 1)
        logger.warning(f"Network error, retry {attempt + 1}/{max_retries} in {wait_time}s")
        time.sleep(wait_time)
        return True

    def handle_format_error(
        self, attempt: int, opts: dict, url: str, quality_format_map: dict[str, str]
    ) -> bool:
        """Handle format error using fallback strategy.

        Args:
            attempt: Current attempt number (0-indexed)
            opts: yt-dlp options dictionary (modified in place)
            url: Video URL for format listing
            quality_format_map: Quality format mapping from config

        Returns:
            True to continue retrying, False if all fallbacks exhausted
        """
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

        strategy = fallback_strategies.get(attempt)
        if not strategy:
            self._log_format_failure(opts, url)
            return False

        format_type, message = strategy
        logger.warning(message)
        opts["format"] = format_type
        return True

    def _log_format_failure(self, opts: dict, url: str) -> None:
        """Log detailed information about format failure.

        Args:
            opts: yt-dlp options dictionary
            url: Video URL for format listing
        """
        logger.error("All format attempts failed. This may be due to:")
        logger.error("  1. Outdated yt-dlp version (run: pip install -U yt-dlp)")
        logger.error("  2. YouTube access restrictions or region-locking")
        logger.error("  3. Need for browser cookies to access the video")

        try:
            logger.info("Attempting to list available formats...")
            list_opts = opts.copy()
            list_opts.pop("format", None)
            with yt_dlp.YoutubeDL(list_opts) as ydl:  # type: ignore
                info = ydl.extract_info(url, download=False)
                if info and isinstance(info, dict) and "formats" in info:
                    logger.info(f"Available formats for {url}:")
                    formats = info.get("formats", [])
                    if isinstance(formats, list):
                        for fmt in formats[:10]:
                            logger.info(
                                f"  Format {fmt.get('format_id', 'unknown')}: "
                                f"{fmt.get('format_note', 'N/A')} - "
                                f"{fmt.get('ext', 'unknown')} - "
                                f"height={fmt.get('height', 'N/A')}"
                            )
                    else:
                        logger.warning("Formats is not a list")
        except Exception as list_err:
            logger.warning(f"Could not list formats: {list_err}")

    def log_specific_error(self, error_msg: str) -> None:
        """Log specific error messages based on error content.

        Args:
            error_msg: Error message to analyze
        """
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
