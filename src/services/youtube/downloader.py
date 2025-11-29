from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import yt_dlp

from src.core.enums import DownloadErrorType, ServiceType
from src.core.interfaces import (
    BaseDownloader,
    ICookieHandler,
    IErrorNotifier,
    IFileService,
)

from ...utils.logger import get_logger
from ..file.service import FileService
from ..network.checker import check_site_connection
from .audio_extractor import AudioExtractor
from .error_handler import YouTubeErrorHandler
from .metadata_service import YouTubeMetadataService

if TYPE_CHECKING:
    from src.services.cookies import CookieManager as AutoCookieManager

logger = get_logger(__name__)


class YouTubeDownloader(BaseDownloader):
    def __init__(
        self,
        quality: str | None = None,
        download_playlist: bool = False,
        audio_only: bool = False,
        video_only: bool = False,
        format: str = "video",
        cookie_manager: ICookieHandler | None = None,
        auto_cookie_manager: AutoCookieManager | None = None,
        download_subtitles: bool = False,
        selected_subtitles: list | None = None,
        download_thumbnail: bool = True,
        embed_metadata: bool = True,
        speed_limit: int | None = None,
        retries: int | None = None,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config=None,
    ):
        from src.core.config import get_config as _get_config

        if config is None:
            config = _get_config()
        super().__init__(error_handler, file_service, config)
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
        if not self.file_service:
            self.file_service = FileService()
        self.metadata_service = YouTubeMetadataService(
            error_handler=error_handler, config=self.config
        )
        self.audio_extractor = AudioExtractor(config=self.config, error_handler=error_handler)
        self.youtube_error_handler = YouTubeErrorHandler(error_handler=error_handler)
        self.ytdl_opts = self._get_simple_ytdl_options()
        self._extract_audio_separately = False

    def _add_subtitle_options(self, options: dict[str, Any]) -> None:
        if not (self.download_subtitles and self.selected_subtitles):
            return

        options["writesubtitles"] = True
        options["writeautomaticsub"] = True
        options["subtitlesformat"] = "srt"

        subtitle_langs = [
            sub.get("language_code") or sub.get("id")
            for sub in self.selected_subtitles
            if isinstance(sub, dict) and (sub.get("language_code") or sub.get("id"))
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

    def _get_cookie_path(self) -> str | None:
        if self.auto_cookie_manager:
            if not self.auto_cookie_manager.is_ready():
                if self.auto_cookie_manager.is_generating():
                    logger.warning(
                        "[YOUTUBE_DOWNLOADER] Cookies are still generating, download may fail for age-restricted content"
                    )
                else:
                    logger.warning("[YOUTUBE_DOWNLOADER] Auto cookie manager not ready")
            else:
                try:
                    cookie_path = self.auto_cookie_manager.get_cookies()
                    if cookie_path:
                        logger.info(
                            f"[YOUTUBE_DOWNLOADER] Using auto-generated cookies: {cookie_path}"
                        )
                        return cookie_path
                except Exception as e:
                    logger.error(f"[YOUTUBE_DOWNLOADER] Error getting auto-generated cookies: {e}")

        if self.cookie_manager:
            cookie_path = self.cookie_manager.get_cookies()
            if cookie_path:
                logger.info(f"[YOUTUBE_DOWNLOADER] Using cookie manager cookies: {cookie_path}")
                return cookie_path
        return None

    def _get_simple_ytdl_options(self) -> dict[str, Any]:
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
            "extractor_args": {
                "youtube": {"player_client": ["android", "ios", "tv_embedded", "web"]}
            },
            "writethumbnail": self.download_thumbnail,
            "embedmetadata": self.embed_metadata,
        }

        if self.speed_limit:
            options["ratelimit"] = self.speed_limit * self.config.downloads.kb_to_bytes

        self._add_subtitle_options(options)

        cookie_path = self._get_cookie_path()
        if cookie_path:
            options["cookiefile"] = cookie_path

        if not self.download_playlist:
            options["noplaylist"] = True
            options["playlist_items"] = self.config.youtube.playlist_item_limit

        return options

    def _configure_audio_format(
        self, opts: dict[str, Any], output_template: str
    ) -> tuple[str, str]:
        opts["format"] = "bestaudio/best"
        opts["outtmpl"] = {"default": output_template}
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
        return ext, output_template + ext

    def _configure_video_only_format(
        self, opts: dict[str, Any], output_template: str
    ) -> tuple[str, str]:
        if self.quality.endswith("p"):
            height = self.quality.replace("p", "")
            if height.isdigit():
                opts["format"] = (
                    f"bestvideo[height<={height}][ext=mp4]/bestvideo[height<={height}]/bestvideo[ext=mp4]/bestvideo/best[height>=360]/best"
                )
            else:
                opts["format"] = "bestvideo[ext=mp4]/bestvideo/best[height>=360]/best"
        else:
            opts["format"] = "bestvideo[ext=mp4]/bestvideo/best[height>=360]/best"
        ext = ".mp4"
        opts["outtmpl"] = {"default": output_template + ext}
        return ext, output_template + ext

    def _configure_video_audio_format(
        self, opts: dict[str, Any], output_template: str
    ) -> tuple[str, str]:
        format_map = {
            "highest": self.config.youtube.quality_format_map["highest"],
            "lowest": self.config.youtube.quality_format_map["lowest"],
        }

        if self.quality in format_map:
            opts["format"] = format_map[self.quality]
        elif self.quality.endswith("p"):
            height = self.quality.replace("p", "")
            if not height.isdigit():
                logger.warning(f"Invalid quality format: {self.quality}, using best")
                opts["format"] = self.config.youtube.quality_format_map["best"]
            else:
                opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"
                logger.info(f"Using format selection for {self.quality}: {opts['format']}")
        else:
            opts["format"] = self.config.youtube.quality_format_map["best"]
        ext = self.config.youtube.file_extensions["video"]
        opts["outtmpl"] = {"default": output_template + ext}
        self._extract_audio_separately = True
        return ext, output_template + ext

    def _configure_format_options(self, opts: dict[str, Any], output_template: str) -> str:
        if self.format == "audio" or self.audio_only:
            _, expected_path = self._configure_audio_format(opts, output_template)
        elif self.format == "video_only" or self.video_only:
            _, expected_path = self._configure_video_only_format(opts, output_template)
        else:
            _, expected_path = self._configure_video_audio_format(opts, output_template)
        return expected_path

    def _handle_download_error(
        self,
        e: Exception,
        attempt: int,
        max_retries: int,
        retry_wait: float,
        opts: dict[str, Any],
        url: str,
    ) -> bool:
        error_msg = str(e)
        error_type_name = type(e).__name__

        if "DownloadError" not in error_type_name:
            logger.error(f"Error downloading from YouTube: {error_msg}")
            self.youtube_error_handler.log_specific_error(error_msg)
            if self.error_handler:
                self.error_handler.handle_exception(e, "YouTube download", "YouTube")
            return False

        logger.warning(f"YouTube download error (attempt {attempt + 1}/{max_retries}): {error_msg}")

        error_type = self.youtube_error_handler.classify_error(error_msg)
        error_handlers = {
            DownloadErrorType.RATE_LIMIT: lambda a=attempt,
            rw=retry_wait: self.youtube_error_handler.handle_rate_limit_error(a, rw),
            DownloadErrorType.NETWORK: lambda a=attempt,
            mr=max_retries,
            rw=retry_wait,
            em=error_msg: self.youtube_error_handler.handle_network_error(a, mr, rw, em),
            DownloadErrorType.FORMAT: lambda a=attempt: self.youtube_error_handler.handle_format_error(
                a, opts, url, self.config.youtube.quality_format_map
            ),
        }

        handler = error_handlers.get(error_type)
        if handler and handler():
            return True

        if not handler:
            self.youtube_error_handler.log_specific_error(error_msg)

        if self.error_handler:
            self.error_handler.handle_exception(e, "YouTube download", "YouTube")
        return False

    def _perform_download_attempts(self, opts: dict[str, Any], url: str) -> bool:
        max_retries = self.config.downloads.retry_count
        retry_wait = self.config.youtube.default_retry_wait

        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        error_msg = "No video information extracted from YouTube"
                        logger.warning(f"{error_msg} (attempt {attempt + 1}/{max_retries})")

                        should_retry = self._handle_info_extraction_failure(
                            attempt, max_retries, opts, url, error_msg
                        )
                        if not should_retry:
                            if self.error_handler:
                                self.error_handler.handle_service_failure(
                                    "YouTube", "download", error_msg, url
                                )
                            return False
                        continue
                    return True

            except Exception as e:
                should_retry = self._handle_download_error(
                    e, attempt, max_retries, retry_wait, opts, url
                )
                if not should_retry:
                    return False

        error_msg = "All download attempts failed"
        logger.error(error_msg)
        if self.error_handler:
            self.error_handler.handle_service_failure("YouTube", "download", error_msg, url)
        return False

    def _handle_info_extraction_failure(
        self, attempt: int, max_retries: int, opts: dict[str, Any], url: str, error_msg: str
    ) -> bool:
        """Handle info extraction failure by trying format fallback."""
        current_format = opts.get("format", "unknown")

        format_fallback_attempts = {
            0: ("best", "Trying 'best' format as fallback"),
            1: ("worst", "Trying 'worst' format as fallback"),
        }

        fallback = format_fallback_attempts.get(attempt)
        if not fallback:
            logger.error(f"All format fallbacks exhausted. Original format: {current_format}")
            return False

        format_type, message = fallback
        logger.warning(message)
        opts["format"] = format_type
        return True

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        connected, error_msg = check_site_connection(ServiceType.YOUTUBE)
        if not connected:
            logger.error(f"Cannot download from YouTube: {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "YouTube", "download", error_msg or "Connection failed", url
                )
            return False

        try:
            save_dir = os.path.dirname(save_path)
            os.makedirs(save_dir, exist_ok=True)

            base_filename = os.path.basename(save_path)
            sanitized_name = self.file_service.sanitize_filename(base_filename)
            output_template = os.path.join(save_dir, sanitized_name)

            opts = self.ytdl_opts.copy()
            expected_output_path = self._configure_format_options(opts, output_template)

            if progress_callback:
                opts["progress_hooks"] = [self._create_progress_hook(progress_callback)]

            logger.info(f"Downloading from YouTube: {url}")
            logger.info(f"Expected output path: {expected_output_path}")

            download_successful = self._perform_download_attempts(opts, url)

            if not download_successful:
                return False

            verified = self._verify_download_completion(expected_output_path)

            if verified and self._extract_audio_separately:
                audio_extracted = self.audio_extractor.extract_audio(expected_output_path)
                if not audio_extracted:
                    logger.warning(
                        "[YOUTUBE_DOWNLOADER] Video downloaded but audio extraction failed"
                    )

            return verified

        except Exception as e:
            logger.error(f"Unexpected error downloading from YouTube: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "YouTube download", "YouTube")
            return False

    def _verify_download_completion(self, output_path: str) -> bool:
        logger.info(f"[VERIFICATION] Checking if download completed: {output_path}")

        if not os.path.exists(output_path):
            logger.error(f"[VERIFICATION] Expected file does not exist: {output_path}")

            part_file = output_path + ".part"
            if os.path.exists(part_file):
                logger.error(f"[VERIFICATION] Found incomplete .part file: {part_file}")
                logger.error("[VERIFICATION] Download was interrupted or failed")
                return False

            temp_file = output_path + ".temp"
            if os.path.exists(temp_file):
                logger.error(f"[VERIFICATION] Found incomplete .temp file: {temp_file}")
                return False

            logger.error("[VERIFICATION] No output file or partial file found")
            return False

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
        start_time = time.time()

        def hook(d):
            status = d.get("status")

            if status == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                progress = downloaded / total * 100 if total > 0 else 0

                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0

                callback(progress, speed)

            elif status == "finished":
                filename = d.get("filename", "")
                d.get("info_dict", {})

                is_subtitle = filename.endswith((".vtt", ".srt", ".ass", ".sub"))
                is_thumbnail = filename.endswith((".jpg", ".png", ".webp"))

                if not is_subtitle and not is_thumbnail:
                    logger.debug(f"Main download finished: {filename}")
                    callback(100.0, 0.0)
                else:
                    logger.debug(f"Auxiliary file finished: {filename}")

            elif status == "error":
                logger.error(f"Download error in progress hook: {d.get('error', 'Unknown error')}")

        return hook
