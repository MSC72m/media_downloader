"""YouTube link handler implementation."""

import re
from collections.abc import Callable
from typing import Any

from src.core.config import AppConfig, get_config
from src.core.enums.message_level import MessageLevel
from src.core.interfaces import (
    IAutoCookieManager,
    ICookieHandler,
    IErrorNotifier,
    IMessageQueue,
    IMetadataService,
)
from src.core.models import Download
from src.services.detection.base_handler import BaseHandler
from src.services.detection.link_detector import (
    auto_register_handler,
)
from src.services.events.queue import Message
from src.ui.dialogs.input_dialog import CenteredInputDialog
from src.ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog
from src.utils.error_helpers import extract_error_context
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_platform_callback,
    get_root,
    get_ui_context,
    safe_getattr,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class YouTubeHandler(BaseHandler):
    def __init__(
        self,
        cookie_handler: ICookieHandler,
        metadata_service: IMetadataService,
        auto_cookie_manager: IAutoCookieManager,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config, service_name="youtube")
        self.cookie_handler = cookie_handler
        self.metadata_service = metadata_service
        self.auto_cookie_manager = auto_cookie_manager
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().youtube.url_patterns

    def _extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract YouTube-specific metadata from URL."""
        return {
            "type": self._detect_youtube_type(url),
            "video_id": self._extract_video_id(url),
            "playlist_id": self._extract_playlist_id(url),
            "is_music": self._is_youtube_music(url),
        }

    def get_metadata(self, url: str) -> dict[str, Any]:
        """Get YouTube metadata for the URL."""
        try:
            video_info = self.metadata_service.fetch_metadata(url)

            return {
                "title": safe_getattr(video_info, "title", "Unknown"),
                "duration": safe_getattr(video_info, "duration", 0),
                "view_count": safe_getattr(video_info, "view_count", 0),
                "thumbnail": safe_getattr(video_info, "thumbnail_url", ""),
                "available_qualities": safe_getattr(video_info, "available_qualities", []),
                "available_formats": safe_getattr(video_info, "available_formats", []),
                "available_subtitles": safe_getattr(video_info, "available_subtitles", []),
            }
        except Exception as e:
            logger.error(f"Error getting YouTube metadata: {e}")
            return {}

    def process_download(self, url: str, options: dict[str, Any]) -> bool:
        """Process YouTube download."""
        logger.info(f"[YOUTUBE_HANDLER] Processing YouTube download: {url}")
        logger.debug(f"[YOUTUBE_HANDLER] Options: {options}")
        # Actual download logic would go here
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for YouTube URLs."""
        logger.info("[YOUTUBE_HANDLER] Getting UI callback")

        def youtube_callback(url: str, ui_context: Any):
            """Callback for handling YouTube URLs."""
            logger.info(f"[YOUTUBE_HANDLER] YouTube callback called with URL: {url}")

            # Early return if no download callback
            download_callback = get_platform_callback(ui_context, "youtube")
            if not download_callback:
                error_msg = "No download callback found"
                logger.error(f"[YOUTUBE_HANDLER] {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "YouTube Handler", "callback", error_msg, url
                    )
                return

            # Early return if cookies are generating - reject URL
            if self._is_cookie_generating(ui_context):
                logger.warning("[YOUTUBE_HANDLER] Cookies are being generated, rejecting URL")
                self._show_cookie_generating_message(ui_context)
                return

            root = get_root(ui_context)

            # Check if this is a YouTube Music URL - show name dialog before downloading as audio
            is_music = self._is_youtube_music(url)
            if is_music:
                logger.info("[YOUTUBE_HANDLER] YouTube Music URL detected - showing name dialog")

                def show_music_name_dialog():
                    try:
                        track_name = "YouTube Music"
                        if self.metadata_service:
                            try:
                                metadata = self.metadata_service.fetch_metadata(url)
                                if metadata and metadata.title:
                                    track_name = metadata.title
                                    logger.info(
                                        f"[YOUTUBE_HANDLER] Music metadata fetched: {track_name}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"[YOUTUBE_HANDLER] Could not fetch music metadata: {e}",
                                    exc_info=True,
                                )
                                if self.error_handler:
                                    extract_error_context(e, "YouTube", "metadata fetch", url)
                                    self.error_handler.handle_exception(
                                        e, "Fetching music metadata", "YouTube"
                                    )

                        dialog = CenteredInputDialog(
                            text="Enter a name for this track:",
                            title="YouTube Music Download",
                        )
                        if track_name != "YouTube Music":
                            dialog._entry.delete(0, "end")
                            dialog._entry.insert(0, track_name)

                        name = dialog.get_input()

                        if not name:
                            logger.info(
                                "[YOUTUBE_HANDLER] User cancelled YouTube Music name dialog"
                            )
                            return

                        download = Download(
                            url=url,
                            name=name,
                            service_type="youtube",
                        )

                        download.audio_only = True
                        download.format = "audio"
                        download.quality = "best"
                        download.download_thumbnail = True
                        download.embed_metadata = True

                        download_callback(download)
                        logger.info(f"[YOUTUBE_HANDLER] YouTube Music download added: {name}")

                    except Exception as e:
                        logger.error(
                            f"[YOUTUBE_HANDLER] Failed to create music download: {e}",
                            exc_info=True,
                        )
                        if self.error_handler:
                            extract_error_context(e, "YouTube", "music download creation", url)
                            self.error_handler.handle_exception(
                                e, "Creating YouTube Music download", "YouTube"
                            )
                        elif self.message_queue:
                            self.message_queue.add_message(
                                Message(
                                    text=f"Failed to add YouTube Music download: {str(e)}",
                                    level=MessageLevel.ERROR,
                                    title="YouTube Music Error",
                                )
                            )

                schedule_on_main_thread(root, show_music_name_dialog, immediate=True)
                return

            # For regular YouTube videos, go directly to YouTube dialog
            # Auto cookie manager will provide cookies automatically
            def create_youtube_dialog():
                try:
                    logger.info("[YOUTUBE_HANDLER] Creating YouTubeDownloaderDialog")

                    # Get auto-generated cookies if available
                    cookie_path = None
                    if self.auto_cookie_manager and self.auto_cookie_manager.is_ready():
                        try:
                            cookie_path = self.auto_cookie_manager.get_cookies()
                            logger.info(
                                f"[YOUTUBE_HANDLER] Using auto-generated cookies: {cookie_path}"
                            )
                        except Exception as cookie_error:
                            logger.warning(
                                f"[YOUTUBE_HANDLER] Failed to get auto cookies: {cookie_error}"
                            )
                    else:
                        logger.warning("[YOUTUBE_HANDLER] Auto cookies not ready yet")

                    YouTubeDownloaderDialog(
                        root,
                        url=url,
                        cookie_handler=self.cookie_handler,
                        metadata_service=self.metadata_service,
                        on_download=download_callback,
                        pre_fetched_metadata=None,
                        initial_cookie_path=cookie_path,
                        error_handler=self.error_handler,
                        message_queue=self.message_queue,
                    )
                    logger.info("[YOUTUBE_HANDLER] YouTubeDownloaderDialog created successfully")
                except Exception as e:
                    logger.error(
                        f"[YOUTUBE_HANDLER] Failed to create YouTubeDownloaderDialog: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        extract_error_context(e, "YouTube", "dialog creation", url)
                        self.error_handler.handle_exception(e, "Creating YouTube dialog", "YouTube")

            # Schedule dialog creation on main thread (non-blocking)
            schedule_on_main_thread(root, create_youtube_dialog, immediate=True)
            logger.info("[YOUTUBE_HANDLER] YouTubeDownloaderDialog creation scheduled")

        logger.info("[YOUTUBE_HANDLER] Returning YouTube callback")
        return youtube_callback

    def _detect_youtube_type(self, url: str) -> str:
        """Detect if URL is video, playlist, etc."""
        type_markers = [
            ("playlist?list=", "playlist"),
            ("shorts/", "shorts"),
            ("watch?v=", "video"),
            ("youtu.be/", "video"),
            ("embed/", "embed"),
            ("v/", "embed"),
        ]

        for marker, content_type in type_markers:
            if marker in url:
                return content_type

        return "unknown"

    def _extract_video_id(self, url: str) -> str | None:
        """Extract video ID from YouTube URL."""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_playlist_id(self, url: str) -> str | None:
        """Extract playlist ID from YouTube URL."""
        match = re.search(r"list=([0-9A-Za-z_-]+)", url)
        return match.group(1) if match else None

    def _is_youtube_music(self, url: str) -> bool:
        """Check if URL is from YouTube Music.

        Args:
            url: URL to check

        Returns:
            True if URL is from music.youtube.com
        """
        return "music.youtube.com" in url.lower()

    def _is_cookie_generating(self, ui_context: Any) -> bool:
        """Check if cookies are currently being generated.

        Args:
            ui_context: UI context (for potential future use)

        Returns:
            True if cookies are generating, False otherwise
        """
        # Check direct state first
        if self.auto_cookie_manager.is_generating():
            logger.info("[YOUTUBE_HANDLER] Cookie manager reports cookies are generating")
            return True

        # Check state object for real-time updates
        state = self.auto_cookie_manager.get_state()
        if state is not None and state.is_generating:
            logger.info("[YOUTUBE_HANDLER] Cookie state reports cookies are generating")
            return True

        # Also check generator state directly for real-time updates
        generator_state = self.auto_cookie_manager.generator.get_state()
        if generator_state and generator_state.is_generating:
            logger.info("[YOUTUBE_HANDLER] Cookie generator reports cookies are generating")
            return True

        return False

    def _show_cookie_generating_message(self, ui_context: Any) -> None:
        """Show status bar message when cookies are being generated and reject URL.

        Args:
            ui_context: UI context to get status bar callback
        """
        logger.info("[YOUTUBE_HANDLER] Showing cookie generating message in status bar")
        message_text = "Generating YouTube cookies, please wait for few seconds and try again"

        # Try to get status bar update callback from event coordinator
        ctx = get_ui_context(ui_context)
        if ctx:
            downloads = getattr(ctx, "downloads", None)
            if downloads:
                status_callback = downloads._get_ui_callback("update_status")
                if status_callback:
                    status_callback(message_text, is_error=False)
                    logger.info(
                        "[YOUTUBE_HANDLER] Status bar updated with cookie generation message"
                    )
                    return

        # Fallback to message queue
        if not self.message_queue:
            logger.warning(
                "[YOUTUBE_HANDLER] No message queue available for cookie generation message"
            )
            return

        try:
            self.message_queue.add_message(
                Message(
                    text=message_text,
                    level=MessageLevel.INFO,
                    title="Cookie Generation",
                )
            )
            logger.info("[YOUTUBE_HANDLER] Message queue updated with cookie generation message")
        except Exception as e:
            logger.error(f"[YOUTUBE_HANDLER] Failed to add message to queue: {e}", exc_info=True)
