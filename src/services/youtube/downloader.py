"""YouTube downloader service implementation."""

import os
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

import yt_dlp

from src.core.enums import ServiceType, DownloadErrorType
from src.interfaces.service_interfaces import BaseDownloader, ICookieHandler, IErrorHandler
from ..file.sanitizer import FilenameSanitizer
from ..network.checker import check_site_connection
from ...utils.logger import get_logger
from .audio_extractor import AudioExtractor
from .error_handler import YouTubeErrorHandler
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
        self.youtube_error_handler = YouTubeErrorHandler(error_handler=error_handler)
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
            "extractor_args": {"youtube": {"player_client": ["android", "ios", "tv_embedded", "web"]}},  # Try multiple clients, Android first to match mobile cookies
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
            # Only use actual language codes, no default fallback
            subtitle_langs = [
                sub.get("language_code") or sub.get("id")
                for sub in self.selected_subtitles
                if isinstance(sub, dict) and (sub.get("language_code") or sub.get("id"))
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
        # Use early returns and comprehensions
        cookie_path = None
        
        if self.auto_cookie_manager:
            if not self.auto_cookie_manager.is_ready():
                if self.auto_cookie_manager.is_generating():
                    logger.warning("[YOUTUBE_DOWNLOADER] Cookies are still generating, download may fail for age-restricted content")
                else:
                    logger.warning("[YOUTUBE_DOWNLOADER] Auto cookie manager not ready")
            else:
                try:
                    cookie_path = self.auto_cookie_manager.get_cookies()
                    if cookie_path:
                        options["cookiefile"] = cookie_path
                        logger.info(f"[YOUTUBE_DOWNLOADER] Using auto-generated cookies: {cookie_path}")
                except Exception as e:
                    logger.error(f"[YOUTUBE_DOWNLOADER] Error getting auto-generated cookies: {e}")
        
        if not cookie_path and self.cookie_manager:
            cookie_path = self.cookie_manager.get_cookies()
            if cookie_path:
                options["cookiefile"] = cookie_path
                logger.info(f"[YOUTUBE_DOWNLOADER] Using cookie manager cookies: {cookie_path}")

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

                        error_type = self.youtube_error_handler.classify_error(error_msg)
                        error_handlers = {
                            DownloadErrorType.RATE_LIMIT: lambda: self.youtube_error_handler.handle_rate_limit_error(attempt, retry_wait),
                            DownloadErrorType.NETWORK: lambda: self.youtube_error_handler.handle_network_error(attempt, max_retries, retry_wait, error_msg),
                            DownloadErrorType.FORMAT: lambda: self.youtube_error_handler.handle_format_error(attempt, opts, url, self.config.youtube.quality_format_map),
                        }

                        handler = error_handlers.get(error_type)
                        if handler and handler():
                            continue

                        if not handler:
                            self.youtube_error_handler.log_specific_error(error_msg)

                        if self.error_handler:
                            self.error_handler.handle_exception(e, "YouTube download", "YouTube")
                        return False

                        logger.error(f"Error downloading from YouTube: {error_msg}")
                        self.youtube_error_handler.log_specific_error(error_msg)
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
