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
class SpotifyHandler(BaseHandler):
    def __init__(
        self,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config, service_name="spotify")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().spotify.url_patterns

    def _extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract Spotify-specific metadata from URL."""
        return {
            "type": self._detect_spotify_type(url),
            "id": self._extract_spotify_id(url),
        }

    def get_metadata(self, url: str) -> dict[str, Any]:
        """Get Spotify metadata for URL."""
        return {
            "type": self._detect_spotify_type(url),
            "id": self._extract_spotify_id(url),
            "requires_auth": False,
        }

    def process_download(self, url: str, options: dict[str, Any]) -> bool:
        """Process Spotify download."""
        logger.info(f"[SPOTIFY_HANDLER] Processing Spotify download: {url}")
        return True

    def get_ui_callback(self) -> Callable:
        """Get UI callback for Spotify URLs."""
        logger.info("[SPOTIFY_HANDLER] Getting UI callback")

        def spotify_callback(url: str, ui_context: Any):
            """Callback for handling Spotify URLs."""
            logger.info(f"[SPOTIFY_HANDLER] Spotify callback called with URL: {url}")

            root = get_root(ui_context)

            download_callback = get_platform_callback(ui_context, "spotify")
            if not download_callback:
                download_callback = get_platform_callback(ui_context, "generic")
                if not download_callback:
                    error_msg = "No download callback found"
                    logger.error(f"[SPOTIFY_HANDLER] {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "Spotify Handler", "callback", error_msg, url
                        )
                    return

            def create_spotify_dialog():
                """Create Spotify downloader dialog."""
                try:
                    from src.ui.dialogs.spotify_downloader_dialog import SpotifyDownloaderDialog

                    logger.info("[SPOTIFY_HANDLER] Creating SpotifyDownloaderDialog")

                    SpotifyDownloaderDialog(
                        root,
                        url=url,
                        on_download=download_callback,
                        error_handler=self.error_handler,
                        message_queue=self.message_queue,
                    )
                    logger.info("[SPOTIFY_HANDLER] SpotifyDownloaderDialog created successfully")

                except Exception as e:
                    logger.error(
                        f"[SPOTIFY_HANDLER] Failed to create Spotify dialog: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        extract_error_context(e, "Spotify", "dialog creation", url)
                        self.error_handler.handle_exception(e, "Creating Spotify dialog", "Spotify")
                    else:
                        self.notifier.notify_user(
                            "error",
                            title="Spotify Download Error",
                            message=f"Failed to create Spotify download dialog: {e!s}",
                        )

            schedule_on_main_thread(root, create_spotify_dialog, immediate=True)
            logger.info("[SPOTIFY_HANDLER] Spotify dialog creation scheduled")

        logger.info("[SPOTIFY_HANDLER] Returning Spotify callback")
        return spotify_callback

    def _detect_spotify_type(self, url: str) -> str:
        """Detect if URL is track, album, playlist, or artist.

        Args:
            url: Spotify URL

        Returns:
            Content type: 'track', 'album', 'playlist', 'artist', or 'unknown'
        """
        patterns = [
            (r"/track/", "track"),
            (r"/album/", "album"),
            (r"/playlist/", "playlist"),
            (r"/artist/", "artist"),
        ]

        for pattern, content_type in patterns:
            if pattern in url:
                return content_type

        return "unknown"

    def _extract_spotify_id(self, url: str) -> str | None:
        """Extract Spotify content ID from URL.

        Args:
            url: Spotify URL

        Returns:
            Spotify content ID or None
        """
        match = re.search(r"/(?:track|album|playlist|artist)/([\w-]+)", url)
        return match.group(1) if match else None
