"""YouTube link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from src.services.detection.link_detector import (
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_container,
    get_platform_callback,
    get_root,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class YouTubeHandler(LinkHandlerInterface):
    """Handler for YouTube URLs."""

    # YouTube URL patterns (including YouTube Music)
    YOUTUBE_PATTERNS = [
        r"^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+",
        r"^https?://(?:www\.)?youtu\.be/[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/embed/[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/v/[\w-]+",
        r"^https?://(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"^https?://music\.youtube\.com/watch\?v=[\w-]+",
        r"^https?://music\.youtube\.com/playlist\?list=[\w-]+",
    ]

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return cls.YOUTUBE_PATTERNS

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is a YouTube URL."""
        logger.debug(f"[YOUTUBE_HANDLER] Testing if can handle URL: {url}")

        for pattern in self.YOUTUBE_PATTERNS:
            if re.match(pattern, url):
                logger.info(f"[YOUTUBE_HANDLER] URL matches pattern: {pattern}")
                result = DetectionResult(
                    service_type="youtube",
                    confidence=1.0,
                    metadata={
                        "type": self._detect_youtube_type(url),
                        "video_id": self._extract_video_id(url),
                        "playlist_id": self._extract_playlist_id(url),
                        "is_music": self._is_youtube_music(url),
                    },
                )
                logger.info(
                    f"[YOUTUBE_HANDLER] Can handle URL with confidence: {result.confidence}"
                )
                logger.debug(f"[YOUTUBE_HANDLER] Detection metadata: {result.metadata}")
                return result

        logger.debug("[YOUTUBE_HANDLER] URL does not match any pattern")
        return DetectionResult(service_type="unknown", confidence=0.0)

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get YouTube metadata for the URL."""
        from src.services.youtube.metadata_service import YouTubeMetadataService
        from src.utils.type_helpers import safe_getattr

        try:
            metadata_service = YouTubeMetadataService()
            video_info = metadata_service.fetch_metadata(url)

            return {
                "title": safe_getattr(video_info, "title", "Unknown"),
                "duration": safe_getattr(video_info, "duration", 0),
                "view_count": safe_getattr(video_info, "view_count", 0),
                "thumbnail": safe_getattr(video_info, "thumbnail_url", ""),
                "available_qualities": safe_getattr(
                    video_info, "available_qualities", []
                ),
                "available_formats": safe_getattr(video_info, "available_formats", []),
                "available_subtitles": safe_getattr(
                    video_info, "available_subtitles", []
                ),
            }
        except Exception as e:
            logger.error(f"Error getting YouTube metadata: {e}")
            return {}

    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process YouTube download."""
        # This would integrate with your download system
        print(f"Processing YouTube download: {url}")
        print(f"Options: {options}")
        # Actual download logic would go here
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for YouTube URLs."""
        logger.info("[YOUTUBE_HANDLER] Getting UI callback")

        from src.ui.dialogs.browser_cookie_dialog import BrowserCookieDialog
        from src.ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog

        def youtube_callback(url: str, ui_context: Any):
            """Callback for handling YouTube URLs."""
            logger.info(f"[YOUTUBE_HANDLER] YouTube callback called with URL: {url}")
            logger.info(f"[YOUTUBE_HANDLER] UI context: {ui_context}")
            logger.info(f"[YOUTUBE_HANDLER] UI context type: {type(ui_context)}")

            # Get container and root using type-safe helpers
            container = get_container(ui_context)
            root = get_root(ui_context)

            logger.info(f"[YOUTUBE_HANDLER] Container: {container}")
            logger.info(f"[YOUTUBE_HANDLER] Root: {root}")

            cookie_handler = container.get("cookie_handler") if container else None
            metadata_service = container.get("youtube_metadata") if container else None

            logger.info(f"[YOUTUBE_HANDLER] Cookie handler: {cookie_handler}")
            logger.info(f"[YOUTUBE_HANDLER] Metadata service: {metadata_service}")

            # Get download callback using type-safe helper
            download_callback = get_platform_callback(ui_context, "youtube")
            if not download_callback:
                logger.error("[YOUTUBE_HANDLER] No download callback found")
                return

            # Check if this is a YouTube Music URL - show name dialog before downloading as audio
            is_music = self._is_youtube_music(url)
            if is_music:
                logger.info(
                    "[YOUTUBE_HANDLER] YouTube Music URL detected - showing name dialog"
                )

                def show_music_name_dialog():
                    try:
                        from src.core.models import Download
                        from src.ui.dialogs.input_dialog import CenteredInputDialog

                        # Fetch metadata first for proper default naming
                        track_name = "YouTube Music"
                        if metadata_service:
                            try:
                                metadata = metadata_service.fetch_metadata(url)
                                if metadata and metadata.title:
                                    track_name = metadata.title
                                    logger.info(
                                        f"[YOUTUBE_HANDLER] Music metadata fetched: {track_name}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"[YOUTUBE_HANDLER] Could not fetch music metadata: {e}"
                                )

                        # Show name dialog with pre-filled default name
                        dialog = CenteredInputDialog(
                            text="Enter a name for this track:",
                            title="YouTube Music Download",
                        )
                        # Pre-fill with fetched track name
                        if track_name != "YouTube Music":
                            dialog._entry.delete(0, "end")
                            dialog._entry.insert(0, track_name)

                        name = dialog.get_input()

                        if not name:
                            logger.info(
                                "[YOUTUBE_HANDLER] User cancelled YouTube Music name dialog"
                            )
                            return

                        # Create download with user-provided name
                        download = Download(
                            url=url,
                            name=name,
                            service_type="youtube",
                        )

                        # Set audio-only options (these will be used by YouTubeDownloader)
                        download.audio_only = True
                        download.format = "audio"
                        download.quality = "best"
                        download.download_thumbnail = True
                        download.embed_metadata = True

                        # Add to download queue via callback
                        download_callback(download)
                        logger.info(
                            f"[YOUTUBE_HANDLER] YouTube Music download added: {name}"
                        )

                    except Exception as e:
                        logger.error(
                            f"[YOUTUBE_HANDLER] Failed to create music download: {e}",
                            exc_info=True,
                        )
                        # Show error to user
                        try:
                            from src.core.enums.message_level import MessageLevel
                            from src.services.events.queue import Message

                            message_queue = (
                                container.get("message_queue") if container else None
                            )
                            if message_queue:
                                message_queue.add_message(
                                    Message(
                                        text=f"Failed to add YouTube Music download: {str(e)}",
                                        level=MessageLevel.ERROR,
                                        title="YouTube Music Error",
                                    )
                                )
                        except Exception as dialog_error:
                            logger.error(
                                f"[YOUTUBE_HANDLER] Failed to show error dialog: {dialog_error}"
                            )

                schedule_on_main_thread(root, show_music_name_dialog, immediate=True)
                return

            # For regular YouTube videos, show cookie selection dialog first
            def on_cookie_selected(cookie_path: Optional[str], browser: Optional[str]):
                logger.info(
                    f"[YOUTUBE_HANDLER] Cookie selected: {cookie_path}, browser: {browser}"
                )

                def create_youtube_dialog():
                    try:
                        # Validate cookie path before proceeding
                        if cookie_path and cookie_handler:
                            success = cookie_handler.set_cookie_file(cookie_path)
                            if not success:
                                logger.error(
                                    f"[YOUTUBE_HANDLER] Failed to set cookie file: {cookie_path}"
                                )
                                # Continue anyway, the dialog will handle the error

                        YouTubeDownloaderDialog(
                            root,
                            url=url,
                            cookie_handler=cookie_handler,
                            metadata_service=metadata_service,
                            on_download=download_callback,
                            pre_fetched_metadata=None,
                            initial_cookie_path=cookie_path,
                            initial_browser=browser,
                        )
                        logger.info(
                            "[YOUTUBE_HANDLER] YouTubeDownloaderDialog created successfully"
                        )
                    except Exception as e:
                        logger.error(
                            f"[YOUTUBE_HANDLER] Failed to create YouTubeDownloaderDialog: {e}",
                            exc_info=True,
                        )

                # Schedule dialog creation on main thread (non-blocking)
                schedule_on_main_thread(root, create_youtube_dialog, immediate=True)
                logger.info(
                    "[YOUTUBE_HANDLER] YouTubeDownloaderDialog creation scheduled"
                )

            def create_cookie_dialog():
                try:
                    logger.info("[YOUTUBE_HANDLER] Creating BrowserCookieDialog")
                    # Check if root is valid before creating dialog
                    if root is None:
                        logger.error(
                            "[YOUTUBE_HANDLER] Root is None, cannot create BrowserCookieDialog"
                        )
                        return

                    BrowserCookieDialog(root, on_cookie_selected)
                    logger.info(
                        "[YOUTUBE_HANDLER] BrowserCookieDialog created successfully"
                    )
                except Exception as e:
                    logger.error(
                        f"[YOUTUBE_HANDLER] Failed to create BrowserCookieDialog: {e}",
                        exc_info=True,
                    )
                    # Fallback to direct YouTube downloader dialog without cookies
                    try:

                        def create_fallback_dialog():
                            YouTubeDownloaderDialog(
                                root,
                                url=url,
                                cookie_handler=cookie_handler,
                                metadata_service=metadata_service,
                                on_download=download_callback,
                            )
                            logger.info(
                                "[YOUTUBE_HANDLER] Created YouTubeDownloaderDialog directly as fallback"
                            )

                        schedule_on_main_thread(
                            root, create_fallback_dialog, immediate=True
                        )
                    except Exception as fallback_error:
                        logger.error(
                            f"[YOUTUBE_HANDLER] Fallback also failed: {fallback_error}",
                            exc_info=True,
                        )

            # Schedule cookie dialog creation on main thread (non-blocking)
            schedule_on_main_thread(root, create_cookie_dialog, immediate=True)
            logger.info("[YOUTUBE_HANDLER] BrowserCookieDialog creation scheduled")

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

    def _extract_video_id(self, url: str) -> Optional[str]:
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

    def _extract_playlist_id(self, url: str) -> Optional[str]:
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
