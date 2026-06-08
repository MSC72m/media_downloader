"""YouTube downloader service implementation."""

import copy
import glob
import os
import shutil
import time
from collections.abc import Callable
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import yt_dlp

from src.core.config import AppConfig, get_config
from src.services.cookies import YouTubeCookieSourceCoordinator
from src.services.network.checker import check_site_connection
from src.services.ytdlp_logger import YTDLPLoggerBridge
from src.utils.logger import get_logger

from ...core.enums import ServiceType
from ...core.interfaces import (
    BaseDownloader,
    IAutoCookieManager,
    ICookieHandler,
    IErrorNotifier,
    IFileService,
)
from ..file.sanitizer import FilenameSanitizer
from .error_handler import YouTubeErrorBucket, YouTubeErrorHandler
from .metadata_service import YouTubeMetadataService

logger = get_logger(__name__)


class YouTubeDownloader(BaseDownloader):
    """YouTube downloader service with cookie support.

    Source priority:
        1. Browser cookies (probed + cached)
        2. Manual cookie file (explicit override)
        3. Generated guest cookies (fallback)
        4. No cookies (last resort)
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
        selected_subtitles: list[dict[str, Any]] | None = None,
        download_thumbnail: bool = True,
        embed_metadata: bool = True,
        speed_limit: int | None = None,
        retries: int = 3,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config: AppConfig = get_config(),
    ) -> None:
        super().__init__(error_handler=error_handler, file_service=file_service, config=config)
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
        self.metadata_service = YouTubeMetadataService(
            error_handler=error_handler,
            auto_cookie_manager=auto_cookie_manager,
            cookie_handler=cookie_handler,
            config=config,
        )
        self.cookie_source_coordinator = YouTubeCookieSourceCoordinator(
            auto_cookie_manager=self.auto_cookie_manager,
            cookie_handler=self.cookie_handler,
            config=config,
        )
        self.youtube_error_handler = YouTubeErrorHandler(error_handler=error_handler)
        self._last_download_error_message: str | None = None
        self.ytdl_opts = self._get_simple_ytdl_options()

    def _get_simple_ytdl_options(self) -> dict[str, Any]:
        """Generate simple yt-dlp options without format specifications."""
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "ignoreconfig": True,
            # Keep extractor failures visible so format fallback logic can respond.
            "ignoreerrors": False,
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
            "logger": YTDLPLoggerBridge("YOUTUBE_DOWNLOADER"),
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

    def _build_auth_strategies(self) -> list[tuple[str, dict[str, Any]]]:
        """Build ordered auth strategies for YouTube access."""
        strategies = self.cookie_source_coordinator.build_auth_strategies(
            include_browser_source=False
        )
        return [(strategy.label, strategy.ytdlp_options) for strategy in strategies]

    def _prepare_format_options(self, opts: dict[str, Any], output_template: str) -> str | None:
        """Configure format selection options and return a preferred output extension hint.

        Args:
            opts: yt-dlp options dict (modified in-place)
            output_template: Base output path without extension

        Returns:
            Preferred extension hint (e.g. ".mp4", ".mp3"), or None.
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
            max_height = self._parse_quality_height(self.quality)
            opts["format"] = self._video_only_selector(max_height=max_height)
            opts["outtmpl"] = {"default": output_template}
            opts.pop("merge_output_format", None)
            return None

        # Default: video + audio
        if self.quality == "lowest":
            opts["format"] = "worst"
        else:
            max_height = self._parse_quality_height(self.quality)
            opts["format"] = self._video_with_audio_selector(max_height=max_height)
            logger.info(f"Using format selection for {self.quality}: {opts['format']}")

        opts["outtmpl"] = {"default": output_template}
        opts["merge_output_format"] = "mp4"
        return ".mp4"

    @staticmethod
    def _parse_quality_height(quality: str) -> int | None:
        if quality in {"best", "highest"}:
            return None

        if quality.endswith("p") and quality[:-1].isdigit():
            return int(quality[:-1])

        alias_map = {
            "4k": 2160,
            "8k": 4320,
        }
        return alias_map.get(quality.strip().lower())

    @staticmethod
    def _video_with_audio_selector(max_height: int | None = None) -> str:
        if max_height is None:
            return "bestvideo*[vcodec!=none]+bestaudio[acodec!=none]/best"
        return (
            f"bestvideo*[height<={max_height}][vcodec!=none]+bestaudio[acodec!=none]"
            f"/best[height<={max_height}]/best"
        )

    @staticmethod
    def _video_only_selector(max_height: int | None = None) -> str:
        if max_height is None:
            return "bestvideo*[vcodec!=none]/bestvideo/best"
        return f"bestvideo*[height<={max_height}][vcodec!=none]/bestvideo/best"

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
        self._last_download_error_message = None
        download_succeeded = False

        transient_error_types = {"rate_limit", "network"}

        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(cast(Any, opts)) as ydl:
                    if not ydl.extract_info(url, download=True):
                        logger.error("No video information extracted from YouTube")
                        if opts.get("format"):
                            self._last_download_error_message = "Requested format is not available"
                        else:
                            self._last_download_error_message = "No video information extracted"
                        break

                    download_succeeded = True
                    break

            except Exception as exc:
                error_type = self._classify_download_error(str(exc))
                if error_type not in transient_error_types:
                    max_retries = 1
                if self._handle_download_exception(
                    exc=exc,
                    attempt=attempt,
                    max_retries=max_retries,
                    retry_wait=retry_wait,
                    opts=opts,
                    url=url,
                ):
                    continue
                break

        if download_succeeded:
            return True

        logger.error("All download attempts failed")
        if self._is_format_error_message(self._last_download_error_message):
            return self._attempt_relaxed_format_download(url, opts)
        return False

    def _handle_download_exception(
        self,
        exc: Exception,
        attempt: int,
        max_retries: int,
        retry_wait: int,
        opts: dict[str, Any],
        url: str,
    ) -> bool:
        """Handle one download exception. Returns True when caller should retry."""
        error_msg = str(exc)
        self._last_download_error_message = error_msg

        if "DownloadError" not in str(type(exc).__name__):
            logger.error(f"Error downloading from YouTube: {error_msg}")
            self._log_specific_error(error_msg)
            return False

        if (bucket := self.youtube_error_handler.classify_ytdlp_error(error_msg)) in {
            YouTubeErrorBucket.BROWSER_UNAVAILABLE,
            YouTubeErrorBucket.KEYCHAIN,
            YouTubeErrorBucket.LOGIN_REQUIRED,
        }:
            logger.warning(
                "[YOUTUBE_DOWNLOADER] Non-retryable auth/source error for current strategy "
                f"(bucket={bucket.value}): {error_msg[:220]}"
            )
            return False

        logger.warning(f"YouTube download error (attempt {attempt + 1}/{max_retries}): {error_msg}")
        error_type = self._classify_download_error(error_msg)
        should_retry = self._dispatch_error(
            error_type,
            attempt,
            max_retries,
            retry_wait,
            error_msg,
            opts,
            url,
        )
        if should_retry:
            return True

        if error_type not in ("rate_limit", "network", "format"):
            self._log_specific_error(error_msg)
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
        match error_type:
            case "rate_limit":
                return self._handle_rate_limit_error(attempt, retry_wait)
            case "network":
                return self._handle_network_error(attempt, max_retries, retry_wait, error_msg)
            case "format":
                return self._handle_format_error(attempt, opts, url)
            case _:
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

        if (normalized_url := self._canonicalize_video_url(url)) != url:
            logger.info("[YOUTUBE_DOWNLOADER] Normalized YouTube URL for download")
            url = normalized_url

        try:
            save_dir = os.path.dirname(save_path)
            os.makedirs(save_dir, exist_ok=True)

            base_filename = os.path.basename(save_path)
            sanitizer = FilenameSanitizer()
            sanitized_name = sanitizer.sanitize_filename(base_filename)
            # Strip existing extension so _prepare_format_options can set the correct one
            stem = os.path.splitext(sanitized_name)[0]
            output_template = os.path.join(save_dir, stem)

            opts = self.ytdl_opts.copy()
            preferred_ext = self._prepare_format_options(opts, output_template)
            expected_output_path = (
                f"{output_template}{preferred_ext}" if preferred_ext else output_template
            )

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
                    return self._verify_download_completion(output_template, preferred_ext)

                logger.warning(f"[YOUTUBE_DOWNLOADER] Strategy failed: {label}")
                bucket = self.youtube_error_handler.classify_ytdlp_error(
                    self._last_download_error_message or ""
                )
                if not self._should_continue_auth_fallback(bucket):
                    logger.warning(
                        "[YOUTUBE_DOWNLOADER] Stopping auth fallback chain after "
                        f"{label} due to error bucket: {bucket.value}"
                    )
                    return False
            return False

        except Exception as e:
            logger.error(f"Unexpected error downloading from YouTube: {e!s}", exc_info=True)
            return False

    def _verify_download_completion(
        self,
        output_template: str,
        preferred_ext: str | None = None,
    ) -> bool:
        """Verify that the download completed and produced a primary media file."""
        preferred_path = f"{output_template}{preferred_ext}" if preferred_ext else output_template
        logger.info(f"[VERIFICATION] Checking if download completed: {preferred_path}")

        candidates: list[str] = []
        if preferred_ext:
            candidates.append(preferred_path)
        candidates.append(output_template)

        discovered = [path for path in glob.glob(f"{output_template}.*") if os.path.isfile(path)]
        discovered.sort(key=os.path.getmtime, reverse=True)
        candidates.extend(discovered)

        # Preserve order while deduplicating.
        unique_candidates: list[str] = []
        seen: set[str] = set()
        for path in candidates:
            if path in seen:
                continue
            seen.add(path)
            unique_candidates.append(path)

        for output_path in unique_candidates:
            if not os.path.exists(output_path):
                continue

            if self._is_auxiliary_output_file(output_path):
                continue

            if (file_size := os.path.getsize(output_path)) == 0:
                logger.error(f"[VERIFICATION] Output file is empty: {output_path}")
                continue

            verified_path = self._normalize_extensionless_output(
                output_template=output_template,
                candidate_path=output_path,
                preferred_path=preferred_path,
                preferred_ext=preferred_ext,
            )

            logger.info(
                f"[VERIFICATION] Download verified successfully: {verified_path} ({file_size} bytes)"
            )
            return True

        part_candidates = [f"{output_template}.part", *glob.glob(f"{output_template}.*.part")]
        for part_file in part_candidates:
            if os.path.exists(part_file):
                logger.error(f"[VERIFICATION] Found incomplete .part file: {part_file}")
                logger.error("[VERIFICATION] Download was interrupted or failed")
                return False

        temp_candidates = [f"{output_template}.temp", *glob.glob(f"{output_template}.*.temp")]
        for temp_file in temp_candidates:
            if os.path.exists(temp_file):
                logger.error(f"[VERIFICATION] Found incomplete .temp file: {temp_file}")
                return False

        logger.error("[VERIFICATION] No media output file found after download")
        return False

    @staticmethod
    def _normalize_extensionless_output(
        output_template: str,
        candidate_path: str,
        preferred_path: str,
        preferred_ext: str | None,
    ) -> str:
        if not preferred_ext:
            return candidate_path
        if candidate_path != output_template:
            return candidate_path
        if os.path.exists(preferred_path):
            return preferred_path

        try:
            os.replace(output_template, preferred_path)
            return preferred_path
        except OSError as exc:
            logger.warning(
                "[VERIFICATION] Could not normalize extensionless output %s -> %s: %s",
                output_template,
                preferred_path,
                exc,
            )
            return candidate_path

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

    @staticmethod
    def _should_continue_auth_fallback(bucket: YouTubeErrorBucket) -> bool:
        """Route fallback behavior by normalized error bucket."""
        match bucket:
            case (
                YouTubeErrorBucket.LOGIN_REQUIRED
                | YouTubeErrorBucket.BROWSER_UNAVAILABLE
                | YouTubeErrorBucket.KEYCHAIN
            ):
                return True
            case YouTubeErrorBucket.NETWORK:
                return True
            case YouTubeErrorBucket.FORMAT:
                return True
            case YouTubeErrorBucket.OTHER:
                return True

    @staticmethod
    def _is_auxiliary_output_file(path: str) -> bool:
        """Return True when file is likely not the primary media output."""
        if (lowered := path.lower()).endswith((".info.json", ".description")):
            return True

        auxiliary_suffixes = {
            ".part",
            ".temp",
            ".ytdl",
            ".json",
            ".webp",
            ".jpg",
            ".jpeg",
            ".png",
            ".vtt",
            ".srt",
            ".ass",
        }
        return any(lowered.endswith(suffix) for suffix in auxiliary_suffixes)

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

    def _handle_format_error(self, attempt: int, opts: dict[str, Any], url: str) -> bool:
        """Handle format error using fallback strategy."""
        fallback_strategies = {
            0: (
                "best",
                f"Format not available ({opts.get('format', 'unknown')}), retrying with 'best'",
            ),
            1: ("worst", "Best format failed, trying 'worst' as fallback"),
        }

        if not (strategy := fallback_strategies.get(attempt)):
            self._log_format_failure(opts, url)
            return False

        format_type, message = strategy
        logger.warning(message)
        opts["format"] = format_type
        return True

    def _attempt_relaxed_format_download(self, url: str, opts: dict[str, Any]) -> bool:
        """Try one final relaxed format selector before giving up."""
        relaxed_opts = copy.deepcopy(opts)
        relaxed_opts["format"] = self._relaxed_format_selector()

        logger.warning(
            "[YOUTUBE_DOWNLOADER] Retrying with relaxed selector after format failures: "
            f"{relaxed_opts['format']}"
        )

        try:
            with yt_dlp.YoutubeDL(cast(Any, relaxed_opts)) as ydl:
                if not ydl.extract_info(url, download=True):
                    self._last_download_error_message = "No video information extracted"
                    return False
                self._last_download_error_message = None
                return True
        except Exception as exc:
            self._last_download_error_message = str(exc)
            logger.warning(
                "[YOUTUBE_DOWNLOADER] Relaxed format retry failed: %s",
                self._last_download_error_message,
            )
            return False

    def _relaxed_format_selector(self) -> str:
        if self.format == "audio" or self.audio_only:
            return "bestaudio/best"
        if self.format == "video_only" or self.video_only:
            return "bestvideo/best"
        return "bv*+ba/b"

    @staticmethod
    def _is_format_error_message(error_message: str | None) -> bool:
        if not error_message:
            return False
        lowered = error_message.lower()
        indicators = (
            "requested format is not available",
            "no video formats found",
            "format is not available",
        )
        return any(indicator in lowered for indicator in indicators)

    @staticmethod
    def _canonicalize_video_url(url: str) -> str:
        """Strip playlist context when a watch URL already contains a concrete video id."""
        parsed = urlparse(url)
        if (parsed.hostname or "").lower() not in {
            "www.youtube.com",
            "youtube.com",
            "m.youtube.com",
            "music.youtube.com",
        }:
            return url
        if parsed.path != "/watch":
            return url

        if not (video_id := parse_qs(parsed.query).get("v", [None])[0]):
            return url
        return f"https://www.youtube.com/watch?v={video_id}"

    def _log_format_failure(self, opts: dict[str, Any], url: str) -> None:
        """Log detailed information about format failure."""
        logger.error("All format attempts failed. This may be due to:")
        logger.error("  1. Outdated yt-dlp version (run: pip install -U yt-dlp)")
        logger.error("  2. YouTube access restrictions or region-locking")
        logger.error("  3. Need for browser cookies to access the video")

        try:
            logger.info("Attempting to list available formats...")
            list_opts = opts.copy()
            list_opts.pop("format", None)
            with yt_dlp.YoutubeDL(cast(Any, list_opts)) as ydl:
                if (
                    (info := ydl.extract_info(url, download=False))
                    and isinstance(info, dict)
                    and "formats" in info
                ):
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
    def _create_progress_hook(
        callback: Callable[[float, float], None],
    ) -> Callable[[dict[str, Any]], None]:
        """Create a progress hook function for yt-dlp."""
        start_time = time.time()

        def hook(d: dict[str, Any]) -> None:
            try:
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
                    logger.error(
                        f"Download error in progress hook: {d.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")

        return hook
