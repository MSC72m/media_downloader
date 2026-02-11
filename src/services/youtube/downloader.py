"""YouTube downloader service implementation."""

import copy
import os
import shutil
import time
from collections.abc import Callable
from typing import Any

import yt_dlp

from src.services.network.checker import check_site_connection
from src.utils.logger import get_logger

from ...core.enums import ServiceType
from ...core.interfaces import BaseDownloader, IAutoCookieManager, ICookieHandler
from ..file.sanitizer import FilenameSanitizer
from .metadata_service import YouTubeMetadataService

logger = get_logger(__name__)


class YouTubeDownloader(BaseDownloader):
    """YouTube downloader service with cookie support.

    Cookie priority:
        1. auto_cookie_manager (Playwright-generated or managed cookies)
        2. cookie_handler (manual cookie file from user)
        3. Browser cookies fallback (--cookies-from-browser chrome)
    """

    def __init__(
        self,
        quality: str = "720p",
        download_playlist: bool = False,
        audio_only: bool = False,
        video_only: bool = False,
        format: str = "video",
        cookie_handler: ICookieHandler | None = None,
        auto_cookie_manager: IAutoCookieManager | None = None,
        download_subtitles: bool = False,
        selected_subtitles: list | None = None,
        download_thumbnail: bool = True,
        embed_metadata: bool = True,
        speed_limit: int | None = None,
        retries: int = 3,
    ):
        self.quality = quality
        self.download_playlist = download_playlist
        self.audio_only = audio_only
        self.video_only = video_only
        self.format = format
        self.cookie_handler = cookie_handler
        self.auto_cookie_manager = auto_cookie_manager
        self.download_subtitles = download_subtitles
        self.selected_subtitles = selected_subtitles or []
        self.download_thumbnail = download_thumbnail
        self.embed_metadata = embed_metadata
        self.speed_limit = speed_limit
        self.retries = retries
        self.metadata_service = YouTubeMetadataService()
        self.ytdl_opts = self._get_simple_ytdl_options()

    def _get_simple_ytdl_options(self) -> dict[str, Any]:
        """Generate simple yt-dlp options without format specifications."""
        options = {
            "quiet": True,
            "no_warnings": True,
            "ignoreconfig": True,
            "ignoreerrors": True,
            "retries": self.retries,
            "fragment_retries": self.retries,
            "retry_sleep_functions": {"fragment": lambda x: 3 * (x + 1)},
            "socket_timeout": 15,
            "extractor_retries": self.retries,
            "hls_prefer_native": True,
            "nocheckcertificate": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "writethumbnail": self.download_thumbnail,
            "embedmetadata": self.embed_metadata,
        }

        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
            options["remote_components"] = "ejs:github"

        # Add speed limit if specified
        if self.speed_limit:
            options["ratelimit"] = self.speed_limit * 1024  # Convert KB/s to bytes/s

        self._add_subtitle_options(options)

        # Handle playlists
        if not self.download_playlist:
            options["noplaylist"] = True
            options["playlist_items"] = "1"

        return options

    def _add_subtitle_options(self, options: dict[str, Any]) -> None:
        """Add subtitle-related options if subtitles are selected."""
        if not (self.download_subtitles and self.selected_subtitles):
            return

        options["writesubtitles"] = True
        options["writeautomaticsub"] = True
        options["subtitlesformat"] = "srt"
        subtitle_langs = [
            sub.get("language_code", sub.get("id", "en"))
            for sub in self.selected_subtitles
            if isinstance(sub, dict)
        ]
        if subtitle_langs:
            options["subtitleslangs"] = subtitle_langs

        if "postprocessors" not in options:
            options["postprocessors"] = []

        options["postprocessors"].append(
            {
                "key": "FFmpegSubtitlesConvertor",
                "format": "srt",
            }
        )

    def _resolve_auto_cookie_path(self) -> str | None:
        """Resolve auto-managed cookie path, if available."""
        if self.auto_cookie_manager:
            try:
                if self.auto_cookie_manager.is_ready():
                    cookie_path = self.auto_cookie_manager.get_cookies()
                    if cookie_path:
                        logger.info(
                            f"[YOUTUBE_DOWNLOADER] Using auto-managed cookies: {cookie_path}"
                        )
                        return cookie_path
                elif self.auto_cookie_manager.is_generating():
                    logger.warning("[YOUTUBE_DOWNLOADER] Cookies are still generating")
            except Exception as e:
                logger.error(f"[YOUTUBE_DOWNLOADER] Error getting auto-managed cookies: {e}")
        return None

    def _resolve_manual_cookie_path(self) -> str | None:
        """Resolve user-provided manual cookie path, if available."""
        if self.cookie_handler and self.cookie_handler.has_valid_cookies():
            cookie_info = self.cookie_handler.get_cookie_info_for_ytdlp()
            if cookie_info and "cookiefile" in cookie_info:
                logger.info(
                    f"[YOUTUBE_DOWNLOADER] Using manual cookie file: {cookie_info['cookiefile']}"
                )
                return cookie_info["cookiefile"]
        return None

    def _build_auth_strategies(self) -> list[tuple[str, dict[str, Any]]]:
        """Build ordered auth strategies for YouTube access.

        Order favors managed cookies first, then public/no-cookie access, then browser cookies.
        """
        strategies: list[tuple[str, dict[str, Any]]] = []

        auto_cookie = self._resolve_auto_cookie_path()
        if auto_cookie:
            strategies.append(("auto-cookie-file", {"cookiefile": auto_cookie}))

        manual_cookie = self._resolve_manual_cookie_path()
        if manual_cookie and manual_cookie != auto_cookie:
            strategies.append(("manual-cookie-file", {"cookiefile": manual_cookie}))

        strategies.append(("no-cookies", {}))
        strategies.append(("browser-cookies-chrome", {"cookiesfrombrowser": ("chrome",)}))

        return strategies

    def _prepare_format_options(self, opts: dict[str, Any], output_template: str) -> str:
        """Configure format selection options and return expected file extension.

        Args:
            opts: yt-dlp options dict (modified in-place)
            output_template: Base output path without extension

        Returns:
            File extension string (e.g. ".mp4", ".mp3")
        """
        if self.format == "audio" or self.audio_only:
            opts["format"] = "bestaudio/best"
            opts["outtmpl"] = {"default": output_template}
            if "postprocessors" not in opts:
                opts["postprocessors"] = []
            opts["postprocessors"].append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            )
            return ".mp3"

        if self.format == "video_only" or self.video_only:
            opts["format"] = "bestvideo"
            opts["outtmpl"] = {"default": output_template + ".mp4"}
            return ".mp4"

        # Default: video + audio
        format_map = {"highest": "best", "lowest": "worst"}

        if self.quality in format_map:
            opts["format"] = format_map[self.quality]
        elif self.quality.endswith("p"):
            height = self.quality.replace("p", "")
            if not height.isdigit():
                logger.warning(f"Invalid quality format: {self.quality}, using best")
                opts["format"] = "best"
            else:
                opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"
                logger.info(f"Using format selection for {self.quality}: {opts['format']}")
        else:
            opts["format"] = "best"

        opts["outtmpl"] = {"default": output_template + ".mp4"}
        return ".mp4"

    def _attempt_download(
        self,
        url: str,
        opts: dict[str, Any],
        max_retries: int,
        retry_wait: int,
    ) -> bool:
        """Run download with retry logic.

        Returns True on success, False on failure.
        """
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        logger.error("No video information extracted from YouTube")
                        return False
                    return True

            except Exception as e:
                error_msg = str(e)

                if "DownloadError" not in str(type(e).__name__):
                    logger.error(f"Error downloading from YouTube: {error_msg}")
                    self._log_specific_error(error_msg)
                    return False

                logger.warning(
                    f"YouTube download error (attempt {attempt + 1}/{max_retries}): {error_msg}"
                )
                error_type = self._classify_download_error(error_msg)

                should_retry = self._dispatch_error(
                    error_type, attempt, max_retries, retry_wait, error_msg, opts, url
                )
                if should_retry:
                    continue

                if error_type not in ("rate_limit", "network", "format"):
                    self._log_specific_error(error_msg)
                return False

        logger.error("All download attempts failed")
        return False

    def _dispatch_error(
        self,
        error_type: str,
        attempt: int,
        max_retries: int,
        retry_wait: int,
        error_msg: str,
        opts: dict[str, Any],
        url: str,
    ) -> bool:
        """Dispatch error handling by type. Returns True to retry."""
        if error_type == "rate_limit":
            return self._handle_rate_limit_error(attempt, retry_wait)
        if error_type == "network":
            return self._handle_network_error(attempt, max_retries, retry_wait, error_msg)
        if error_type == "format":
            return self._handle_format_error(attempt, opts, url)
        return False

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
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
        connected, error_msg = check_site_connection(ServiceType.YOUTUBE)
        if not connected:
            logger.error(f"Cannot download from YouTube: {error_msg}")
            return False

        try:
            save_dir = os.path.dirname(save_path)
            os.makedirs(save_dir, exist_ok=True)

            base_filename = os.path.basename(save_path)
            sanitizer = FilenameSanitizer()
            sanitized_name = sanitizer.sanitize_filename(base_filename)
            output_template = os.path.join(save_dir, sanitized_name)

            opts = self.ytdl_opts.copy()
            ext = self._prepare_format_options(opts, output_template)
            expected_output_path = output_template + ext

            if progress_callback:
                opts["progress_hooks"] = [self._create_progress_hook(progress_callback)]

            logger.info(f"Downloading from YouTube: {url}")
            logger.info(f"Expected output path: {expected_output_path}")
            auth_strategies = self._build_auth_strategies()
            logger.info(
                "[YOUTUBE_DOWNLOADER] Auth strategies: "
                + ", ".join(label for label, _ in auth_strategies)
            )
            for label, auth_opts in auth_strategies:
                strategy_opts = copy.deepcopy(opts)
                strategy_opts.pop("cookiefile", None)
                strategy_opts.pop("cookiesfrombrowser", None)
                strategy_opts.update(auth_opts)

                logger.info(f"[YOUTUBE_DOWNLOADER] Trying strategy: {label}")
                download_successful = self._attempt_download(
                    url,
                    strategy_opts,
                    max_retries=3,
                    retry_wait=3,
                )
                if download_successful:
                    return self._verify_download_completion(expected_output_path)

                logger.warning(f"[YOUTUBE_DOWNLOADER] Strategy failed: {label}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error downloading from YouTube: {e!s}", exc_info=True)
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
        logger.warning(f"YouTube rate limit hit, waiting {wait_time} seconds before retry")
        time.sleep(wait_time)
        return True

    def _handle_network_error(
        self, attempt: int, max_retries: int, retry_wait: int, error_msg: str
    ) -> bool:
        """Handle network error. Returns True to continue retrying."""
        if attempt >= max_retries - 1:
            logger.error(f"Failed to download after {max_retries} attempts: {error_msg}")
            return False

        wait_time = retry_wait * (attempt + 1)
        logger.warning(f"Network error, retry {attempt + 1}/{max_retries} in {wait_time}s")
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

                progress = (downloaded / total) * 100 if total > 0 else 0

                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0

                callback(progress, speed)

            elif status == "finished":
                # Only report 100% for video files, not subtitles or thumbnails
                filename = d.get("filename", "")

                # Check if this is a subtitle or thumbnail file
                is_subtitle = filename.endswith((".vtt", ".srt", ".ass", ".sub"))
                is_thumbnail = filename.endswith((".jpg", ".png", ".webp"))

                # Only report completion for the main video/audio file
                if not is_subtitle and not is_thumbnail:
                    logger.debug(f"Main download finished: {filename}")
                    callback(100.0, 0.0)
                else:
                    logger.debug(f"Auxiliary file finished: {filename}")

            elif status == "error":
                logger.error(f"Download error in progress hook: {d.get('error', 'Unknown error')}")

        return hook
