"""SoundCloud link handler implementation."""

import re
from collections.abc import Callable
from typing import Any

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.detection.base_handler import BaseHandler
from src.services.detection.link_detector import (
    auto_register_handler,
)
from src.utils.error_helpers import extract_error_context
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_platform_callback,
    get_root,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class SoundCloudHandler(BaseHandler):
    def __init__(
        self,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config, service_name="soundcloud")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().soundcloud.url_patterns

    def _extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract SoundCloud-specific metadata from URL."""
        return {
            "type": self._detect_soundcloud_type(url),
            "username": self._extract_username(url),
            "track_slug": self._extract_track_slug(url),
        }

    def get_metadata(self, url: str) -> dict[str, Any]:
        """Get SoundCloud metadata for the URL."""
        return {
            "type": self._detect_soundcloud_type(url),
            "username": self._extract_username(url),
            "track_slug": self._extract_track_slug(url),
            "requires_auth": False,  # SoundCloud downloads usually work without auth
        }

    def process_download(self, url: str, options: dict[str, Any]) -> bool:
        """Process SoundCloud download."""
        logger.info(f"[SOUNDCLOUD_HANDLER] Processing SoundCloud download: {url}")
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for SoundCloud URLs."""
        logger.info("[SOUNDCLOUD_HANDLER] Getting UI callback")

        def soundcloud_callback(url: str, ui_context: Any):
            """Callback for handling SoundCloud URLs."""
            logger.info(f"[SOUNDCLOUD_HANDLER] SoundCloud callback called with URL: {url}")
            logger.info(f"[SOUNDCLOUD_HANDLER] UI context: {ui_context}")

            # Get root using type-safe helper
            root = get_root(ui_context)

            logger.info(f"[SOUNDCLOUD_HANDLER] Root: {root}")

            download_callback = get_platform_callback(ui_context, "soundcloud")
            if not download_callback:
                download_callback = get_platform_callback(ui_context, "generic")
                if not download_callback:
                    error_msg = "No download callback found"
                    logger.error(f"[SOUNDCLOUD_HANDLER] {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "SoundCloud Handler", "callback", error_msg, url
                        )
                    return

            # Call the platform download method
            def process_soundcloud_download():
                try:
                    logger.info(f"[SOUNDCLOUD_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[SOUNDCLOUD_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[SOUNDCLOUD_HANDLER] Error processing SoundCloud download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        extract_error_context(e, "SoundCloud", "download processing", url)
                        self.error_handler.handle_exception(
                            e, "Processing SoundCloud download", "SoundCloud"
                        )
                    else:
                        self.notifier.notify_user(
                            "error",
                            title="SoundCloud Download Error",
                            message=f"Failed to process SoundCloud download: {e!s}",
                        )

            # Schedule on main thread
            schedule_on_main_thread(root, process_soundcloud_download, immediate=True)
            logger.info("[SOUNDCLOUD_HANDLER] SoundCloud download scheduled")

        logger.info("[SOUNDCLOUD_HANDLER] Returning SoundCloud callback")
        return soundcloud_callback

    def _detect_soundcloud_type(self, url: str) -> str:
        """Detect if URL is track, playlist/set, or user profile."""
        if "/sets/" in url:
            return "playlist"
        if re.search(r"soundcloud\.com/[\w-]+/[\w-]+", url):
            return "track"
        if re.search(r"soundcloud\.com/[\w-]+/?$", url):
            return "user"
        return "unknown"

    def _extract_username(self, url: str) -> str | None:
        """Extract username from SoundCloud URL."""
        match = re.search(r"soundcloud\.com/([\w-]+)", url)
        return match.group(1) if match else None

    def _extract_track_slug(self, url: str) -> str | None:
        """Extract track slug from SoundCloud URL."""
        match = re.search(r"soundcloud\.com/[\w-]+/([\w-]+)", url)
        return match.group(1) if match else None
