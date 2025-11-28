"""YouTube downloader service implementation."""

import os
import re
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import yt_dlp

from src.core.enums import ServiceType
from src.interfaces.service_interfaces import BaseDownloader, ICookieHandler, IErrorHandler
from ..file.sanitizer import FilenameSanitizer
from ..network.checker import check_site_connection
from ...utils.logger import get_logger
from .audio_extractor import AudioExtractor
from .metadata_service import YouTubeMetadataService

if TYPE_CHECKING:
    from src.services.cookies import CookieManager as AutoCookieManager

logger = get_logger(__name__)


class YouTubeDownloader(BaseDownloader):
    """YouTube downloader service with cookie support."""

    def __init__(
        self,
        quality: Optional[str] = None,
        download_playlist: bool = False,
        audio_only: bool = False,
        video_only: bool = False,
        format: str = "video",
        cookie_manager: Optional[ICookieHandler] = None,
        auto_cookie_manager: Optional["AutoCookieManager"] = None,
        download_subtitles: bool = False,
        selected_subtitles: Optional[list] = None,
        download_thumbnail: bool = True,
        embed_metadata: bool = True,
        speed_limit: Optional[int] = None,
        retries: Optional[int] = None,
        error_handler: Optional[IErrorHandler] = None,
        config=None,
    ):
        super().__init__(config)
        self.quality = quality or self.config.youtube.default_quality
        self.download_playlist = download_playlist
        self.audio_only = audio_only
        self.video_only = video_only
        self.format = format
        self.cookie_manager = cookie_manager
        self.auto_cookie_manager = auto_cookie_manager
        self.download_subtitles = download_subtitles
        self.selected_subtitles = selected_subtitles or []
        self.download_thumbnail = download_thumbnail
        self.embed_metadata = embed_metadata
        self.speed_limit = speed_limit
        self.retries = retries
        self.error_handler = error_handler
        self.metadata_service = YouTubeMetadataService(error_handler=error_handler, config=self.config)
        self.audio_extractor = AudioExtractor(config=self.config, error_handler=error_handler)
        self.ytdl_opts = self._get_simple_ytdl_options()
        self._extract_audio_separately = False  # Flag for Audio + Video format

    def _get_simple_ytdl_options(self) -> Dict[str, Any]:
        """Generate simple yt-dlp options without format specifications."""
        retry_count = self.retries or self.config.downloads.retry_count
        options = {
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "retries": retry_count,
            "fragment_retries": retry_count,
            "retry_sleep_functions": {
                "fragment": lambda x: self.config.youtube.retry_sleep_multiplier * (x + 1)
            },
            "socket_timeout": self.config.downloads.socket_timeout,
            "extractor_retries": retry_count,
            "hls_prefer_native": True,
            "nocheckcertificate": True,
            "user_agent": self.config.network.user_agent,
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
            "writethumbnail": self.download_thumbnail,
            "embedmetadata": self.embed_metadata,
        }

        # Add speed limit if specified
        if self.speed_limit:
            options["ratelimit"] = self.speed_limit * self.config.downloads.kb_to_bytes

        # Add subtitle options
        if self.download_subtitles and self.selected_subtitles:
            options["writesubtitles"] = True
            options["writeautomaticsub"] = True
            options["subtitlesformat"] = "srt"  # Request SRT format directly
            # Extract language codes from selected subtitles
            subtitle_langs = [
                sub.get("language_code", sub.get("id", "en"))
                for sub in self.selected_subtitles
                if isinstance(sub, dict)
            ]
            if subtitle_langs:
                options["subtitleslangs"] = subtitle_langs

            # Initialize postprocessors list if not exists
            if "postprocessors" not in options:
                options["postprocessors"] = []

            # Add post-processor to convert subtitles to SRT format
            options["postprocessors"].append(
                {
                    "key": "FFmpegSubtitlesConvertor",
                    "format": "srt",
                }
            )

        # Priority order: auto_cookie_manager > old cookie_manager
        if self.auto_cookie_manager:
            # Use new auto-generated cookies
            try:
                if self.auto_cookie_manager.is_ready():
                    cookie_path = self.auto_cookie_manager.get_cookies()
                    if cookie_path:
                        options["cookiefile"] = cookie_path
                        logger.info(
                            f"[YOUTUBE_DOWNLOADER] Using auto-generated cookies: {cookie_path}"
                        )
                    else:
                        logger.warning(
                            "[YOUTUBE_DOWNLOADER] Auto cookie manager ready but no cookie file available"
                        )
                elif self.auto_cookie_manager.is_generating():
                    logger.warning(
                        "[YOUTUBE_DOWNLOADER] Cookies are still generating, download may fail for age-restricted content"
                    )
                else:
                    logger.warning("[YOUTUBE_DOWNLOADER] Auto cookie manager not ready")
            except Exception as e:
                logger.error(
                    f"[YOUTUBE_DOWNLOADER] Error getting auto-generated cookies: {e}"
                )
        elif self.cookie_manager:
            # Fallback to old cookie file system
            cookie_info = self.cookie_manager.get_cookie_info_for_ytdlp()
            if cookie_info:
                options.update(cookie_info)
                logger.info("[YOUTUBE_DOWNLOADER] Using old cookie system")

        # Handle playlists
        if not self.download_playlist:
            options["noplaylist"] = True
            options["playlist_items"] = self.config.youtube.playlist_item_limit

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
        connected, error_msg = check_site_connection(ServiceType.YOUTUBE)
        if not connected:
            logger.error(f"Cannot download from YouTube: {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("YouTube", "download", error_msg or "Connection failed", url)
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
            output_template = os.path.join(save_dir, sanitized_name)

            # Prepare options with output path
            opts = self.ytdl_opts.copy()

            # Add format selection based on format type and quality
            if self.format == "audio" or self.audio_only:
                # Use better format selection for audio with fallback
                # This works for both regular YouTube and YouTube Music
                opts["format"] = "bestaudio/best"
                # Don't add extension to outtmpl - FFmpegExtractAudio will add it
                opts["outtmpl"] = {"default": output_template}
                # Extend postprocessors instead of replacing
                if "postprocessors" not in opts:
                    opts["postprocessors"] = []
                opts["postprocessors"].append(
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": self.config.youtube.audio_codec,
                        "preferredquality": self.config.youtube.quality_format_map["192"],
                    }
                )
                ext = self.config.youtube.file_extensions["audio"]
            elif self.format == "video_only" or self.video_only:
                # Video only without audio - use bestvideo but ensure we get video, not thumbnail
                # Respect quality selection
                if self.quality.endswith("p"):
                    height = self.quality.replace("p", "")
                    if height.isdigit():
                        opts["format"] = f"bestvideo[height<={height}][ext=mp4]/bestvideo[height<={height}]/bestvideo[ext=mp4]/bestvideo/best[height>=360]/best"
                    else:
                        opts["format"] = "bestvideo[ext=mp4]/bestvideo/best[height>=360]/best"
                else:
                    opts["format"] = "bestvideo[ext=mp4]/bestvideo/best[height>=360]/best"
                ext = ".mp4"
                opts["outtmpl"] = {"default": output_template + ext}
            else:
                # Default: video + audio - download video with selected quality
                # Use yt-dlp postprocessor to extract audio while keeping video
                format_map = {
                    "highest": self.config.youtube.quality_format_map["highest"],
                    "lowest": self.config.youtube.quality_format_map["lowest"],
                }

                if self.quality in format_map:
                    opts["format"] = format_map[self.quality]
                elif self.quality.endswith("p"):
                    height = self.quality.replace("p", "")
                    if not height.isdigit():
                        logger.warning(
                            f"Invalid quality format: {self.quality}, using best"
                        )
                        opts["format"] = self.config.youtube.quality_format_map["best"]
                    else:
                        opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"
                        logger.info(
                            f"Using format selection for {self.quality}: {opts['format']}"
                        )
                else:
                    opts["format"] = self.config.youtube.quality_format_map["best"]
                ext = self.config.youtube.file_extensions["video"]
                opts["outtmpl"] = {"default": output_template + ext}
                
                # For "Audio + Video" format, we'll extract audio after video download
                # yt-dlp's FFmpegExtractAudio removes the original, so we do it manually
                self._extract_audio_separately = True

            # Store expected output path for verification
            expected_output_path = output_template + ext

            # Add progress hook if callback provided
            if progress_callback:
                opts["progress_hooks"] = [self._create_progress_hook(progress_callback)]

            logger.info(f"Downloading from YouTube: {url}")
            logger.info(f"Expected output path: {expected_output_path}")

            # Retry mechanism for network issues
            max_retries = self.config.downloads.retry_count
            retry_wait = self.config.youtube.default_retry_wait

            for attempt in range(max_retries):
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore
                        info = ydl.extract_info(url, download=True)
                        if not info:
                            error_msg = "No video information extracted from YouTube"
                            logger.error(error_msg)
                            if self.error_handler:
                                self.error_handler.handle_service_failure("YouTube", "download", error_msg, url)
                            return False

                        download_successful = True
                        break

                except Exception as e:
                    error_msg = str(e)
                    error_type_name = type(e).__name__

                    if "DownloadError" in error_type_name:
                        logger.warning(f"YouTube download error (attempt {attempt + 1}/{max_retries}): {error_msg}")

                        error_type = self._classify_download_error(error_msg)
                        error_handlers = {
                            "rate_limit": lambda: self._handle_rate_limit_error(attempt, retry_wait),
                            "network": lambda: self._handle_network_error(attempt, max_retries, retry_wait, error_msg),
                            "format": lambda: self._handle_format_error(attempt, opts, url),
                        }

                        handler = error_handlers.get(error_type)
                        if handler and handler():
                            continue

                        if not handler:
                            self._log_specific_error(error_msg)

                        if self.error_handler:
                            self.error_handler.handle_exception(e, "YouTube download", "YouTube")
                        return False

                        logger.error(f"Error downloading from YouTube: {error_msg}")
                        self._log_specific_error(error_msg)
                    if self.error_handler:
                        self.error_handler.handle_exception(e, "YouTube download", "YouTube")
                        return False

            if not download_successful:
                error_msg = "All download attempts failed"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure("YouTube", "download", error_msg, url)
                return False

        except Exception as e:
            logger.error(f"Unexpected error downloading from YouTube: {str(e)}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "YouTube download", "YouTube")
            return False

        # Verify the download actually completed successfully
        if download_successful and expected_output_path:
            verified = self._verify_download_completion(expected_output_path)
            
            # For "Audio + Video" format, extract audio separately after video download
            if verified and self._extract_audio_separately:
                audio_extracted = self.audio_extractor.extract_audio(expected_output_path)
                if not audio_extracted:
                    logger.warning("[YOUTUBE_DOWNLOADER] Video downloaded but audio extraction failed")
                    # Don't fail the download if audio extraction fails
            
            return verified

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
        # Use compiled regex patterns for efficient matching instead of string 'in' checks
        rate_limit_pattern = re.compile(r"HTTP Error 429", re.IGNORECASE)
        network_pattern = re.compile(r"(Connection refused|Network Error|Unable to download|Errno 111)", re.IGNORECASE)
        format_pattern = re.compile(r"(Requested format is not available|No video formats found)", re.IGNORECASE)

        if rate_limit_pattern.search(error_msg):
            return "rate_limit"
        if network_pattern.search(error_msg):
            return "network"
        if format_pattern.search(error_msg):
            return "format"

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
                self.config.youtube.quality_format_map["best"],
                f"Format not available ({opts.get('format', 'unknown')}), retrying with 'best'",
            ),
            1: (self.config.youtube.quality_format_map["lowest"], "Best format failed, trying 'worst' as fallback"),
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
                # Only report 100% for video files, not subtitles or thumbnails
                filename = d.get("filename", "")
                info_dict = d.get("info_dict", {})

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
                logger.error(
                    f"Download error in progress hook: {d.get('error', 'Unknown error')}"
                )

        return hook
