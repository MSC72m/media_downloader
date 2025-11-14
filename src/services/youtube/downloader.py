"""YouTube downloader service implementation."""

import os
import time
from typing import Any, Callable, Dict, Optional

import yt_dlp

from src.services.network.checker import check_site_connection
from src.utils.logger import get_logger

from ...core.base import BaseDownloader
from ...core.enums import ServiceType
from ..file.sanitizer import FilenameSanitizer
from .cookie_detector import CookieManager
from .metadata_service import YouTubeMetadataService

logger = get_logger(__name__)


class YouTubeDownloader(BaseDownloader):
    """YouTube downloader service with cookie support."""

    def __init__(
        self,
        quality: str = "720p",
        download_playlist: bool = False,
        audio_only: bool = False,
        cookie_manager: Optional[CookieManager] = None,
        browser: Optional[str] = None,
    ):
        self.quality = quality
        self.download_playlist = download_playlist
        self.audio_only = audio_only
        self.cookie_manager = cookie_manager
        self.browser = browser
        self.metadata_service = YouTubeMetadataService()
        self.ytdl_opts = self._get_simple_ytdl_options()

    def _get_simple_ytdl_options(self) -> Dict[str, Any]:
        """Generate simple yt-dlp options without format specifications."""
        options = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "retries": 3,
            "fragment_retries": 3,
            "retry_sleep_functions": {"fragment": lambda x: 3 * (x + 1)},
            "socket_timeout": 15,
            "extractor_retries": 3,
            "hls_prefer_native": True,
            "nocheckcertificate": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            # NO format specifications - let yt-dlp choose automatically
        }

        # Use cookiesfrom_browser for direct browser cookie access (more reliable)
        if self.browser:
            browser_lower = self.browser.lower()
            options["cookiesfrombrowser"] = (browser_lower,)
            logger.info(f"Using cookiesfrombrowser: {browser_lower}")
        # Fallback to cookie file if available
        elif self.cookie_manager:
            cookie_info = self.cookie_manager.get_youtube_cookie_info()
            if cookie_info:
                options.update(cookie_info)
                logger.info("Using cookie file for YouTube download")

        # Handle playlists
        if not self.download_playlist:
            options["noplaylist"] = True
            options["playlist_items"] = "1"

        return options

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None,
    ) -> bool:
        """
        Download a YouTube video.

        Args:
            url: YouTube URL to download
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        # Check connectivity to YouTube
        connected, error_msg = check_site_connection(ServiceType.YOUTUBE)
        if not connected:
            logger.error(f"Cannot download from YouTube: {error_msg}")
            return False

        download_successful = False
        expected_output_path = None

        try:
            # Create the output directory if it doesn't exist
            save_dir = os.path.dirname(save_path)
            os.makedirs(save_dir, exist_ok=True)

            # Create a filename
            base_filename = os.path.basename(save_path)
            sanitizer = FilenameSanitizer()
            sanitized_name = sanitizer.sanitize_filename(base_filename)

            # Extension depends on audio_only setting
            ext = ".mp3" if self.audio_only else ".mp4"
            output_template = os.path.join(save_dir, sanitized_name)

            # Prepare options with output path
            opts = self.ytdl_opts.copy()
            opts.update(
                {
                    "outtmpl": {"default": output_template + ext},
                }
            )

            # Add format selection based on quality and audio settings
            if self.audio_only:
                opts["format"] = "bestaudio"
                opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ]
            else:
                # Use dictionary-based format selection
                format_map = {
                    "highest": "best",
                    "lowest": "worst",
                }

                if self.quality in format_map:
                    opts["format"] = format_map[self.quality]
                elif self.quality.endswith("p"):
                    height = self.quality.replace("p", "")
                    if not height.isdigit():
                        logger.warning(
                            f"Invalid quality format: {self.quality}, using best"
                        )
                        opts["format"] = "best"
                    else:
                        opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"
                        logger.info(
                            f"Using format selection for {self.quality}: {opts['format']}"
                        )
                else:
                    opts["format"] = "best"

            # Store expected output path for verification
            expected_output_path = output_template + ext

            # Add progress hook if callback provided
            if progress_callback:
                opts["progress_hooks"] = [self._create_progress_hook(progress_callback)]

            logger.info(f"Downloading from YouTube: {url}")
            logger.info(f"Expected output path: {expected_output_path}")

            # Retry mechanism for network issues
            max_retries = 3
            retry_wait = 3  # seconds

            for attempt in range(max_retries):
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                        info = ydl.extract_info(url, download=True)
                        if not info:
                            logger.error("No video information extracted from YouTube")
                            return False

                        # Mark download as potentially successful
                        download_successful = True
                        break  # Exit retry loop

                except Exception as e:
                    error_msg = str(e)

                    # Only handle download errors
                    if "DownloadError" in str(type(e).__name__):
                        logger.warning(
                            f"YouTube download error (attempt {attempt + 1}/{max_retries}): {error_msg}"
                        )

                        # Handle error using dispatcher pattern
                        error_type = self._classify_download_error(error_msg)

                        error_handlers = {
                            "rate_limit": lambda: self._handle_rate_limit_error(
                                attempt, retry_wait
                            ),
                            "network": lambda: self._handle_network_error(
                                attempt, max_retries, retry_wait, error_msg
                            ),
                            "format": lambda: self._handle_format_error(
                                attempt, opts, url
                            ),
                        }

                        handler = error_handlers.get(error_type)
                        if handler and handler():
                            continue

                        if not handler:
                            self._log_specific_error(error_msg)

                        return False
                    else:
                        # Other exceptions
                        logger.error(f"Error downloading from YouTube: {error_msg}")
                        self._log_specific_error(error_msg)
                        return False

            # All retries exhausted
            if not download_successful:
                logger.error("All download attempts failed")
                return False

        except Exception as e:
            logger.error(
                f"Unexpected error downloading from YouTube: {str(e)}", exc_info=True
            )
            return False

        # Verify the download actually completed successfully
        if download_successful and expected_output_path:
            return self._verify_download_completion(expected_output_path)

        return False

    def _verify_download_completion(self, output_path: str) -> bool:
        """Verify that the download actually completed successfully."""
        logger.info(f"[VERIFICATION] Checking if download completed: {output_path}")

        # Check if the expected file exists
        if not os.path.exists(output_path):
            logger.error(f"[VERIFICATION] Expected file does not exist: {output_path}")

            # Check for .part file (incomplete download)
            part_file = output_path + ".part"
            if os.path.exists(part_file):
                logger.error(f"[VERIFICATION] Found incomplete .part file: {part_file}")
                logger.error("[VERIFICATION] Download was interrupted or failed")
                return False

            # Check for .temp file
            temp_file = output_path + ".temp"
            if os.path.exists(temp_file):
                logger.error(f"[VERIFICATION] Found incomplete .temp file: {temp_file}")
                return False

            logger.error("[VERIFICATION] No output file or partial file found")
            return False

        # Check file size (should be > 0)
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            logger.error(f"[VERIFICATION] Output file is empty: {output_path}")
            return False

        logger.info(
            f"[VERIFICATION] Download verified successfully: {output_path} ({file_size} bytes)"
        )
        return True

    def _classify_download_error(self, error_msg: str) -> str:
        """Classify the type of download error using pattern matching."""
        error_patterns = {
            "rate_limit": ["HTTP Error 429"],
            "network": [
                "Connection refused",
                "Network Error",
                "Unable to download",
                "Errno 111",
            ],
            "format": ["Requested format is not available", "No video formats found"],
        }

        for error_type, patterns in error_patterns.items():
            if any(pattern in error_msg for pattern in patterns):
                return error_type

        return "other"

    def _handle_rate_limit_error(self, attempt: int, retry_wait: int) -> bool:
        """Handle rate limit error. Returns True to continue retrying."""
        wait_time = retry_wait * (2**attempt)
        logger.warning(
            f"YouTube rate limit hit, waiting {wait_time} seconds before retry"
        )
        time.sleep(wait_time)
        return True

    def _handle_network_error(
        self, attempt: int, max_retries: int, retry_wait: int, error_msg: str
    ) -> bool:
        """Handle network error. Returns True to continue retrying."""
        if attempt >= max_retries - 1:
            logger.error(
                f"Failed to download after {max_retries} attempts: {error_msg}"
            )
            return False

        wait_time = retry_wait * (attempt + 1)
        logger.warning(
            f"Network error, retry {attempt + 1}/{max_retries} in {wait_time}s"
        )
        time.sleep(wait_time)
        return True

    def _handle_format_error(self, attempt: int, opts: dict, url: str) -> bool:
        """Handle format error using fallback strategy."""
        fallback_strategies = {
            0: (
                "best",
                f"Format not available ({opts.get('format', 'unknown')}), retrying with 'best'",
            ),
            1: ("worst", "Best format failed, trying 'worst' as fallback"),
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
        """Log detailed information about format failure."""
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

    def _log_specific_error(self, error_msg: str) -> None:
        """Log specific error messages based on error content."""
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

        # Default error message
        logger.error(f"YouTube download error: {error_msg}")

    @staticmethod
    def _create_progress_hook(callback: Callable[[float, float], None]):
        """Create a progress hook function for yt-dlp."""
        start_time = time.time()

        def hook(d):
            status = d.get("status")

            if status == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                if total > 0:
                    progress = (downloaded / total) * 100
                else:
                    progress = 0

                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0

                callback(progress, speed)

            elif status == "finished":
                # Report 100% when finished
                logger.debug("Download phase finished")
                callback(100.0, 0.0)

            elif status == "error":
                logger.error(
                    f"Download error in progress hook: {d.get('error', 'Unknown error')}"
                )

        return hook
