import re
from collections.abc import Mapping

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier, IMessageQueue, UIContextProtocol
from src.core.type_defs import JSONDict, JSONValue
from src.services.detection.base_handler import BaseHandler, UICallback
from src.services.detection.link_detector import (
    auto_register_handler,
)
from src.services.instagram.auth_manager import InstagramAuthManager
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_platform_callback,
    get_root,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class InstagramHandler(BaseHandler):
    def __init__(
        self,
        instagram_auth_manager: InstagramAuthManager,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        super().__init__(message_queue, resolved_config, service_name="instagram")
        # Retained for factory-level sharing of an authenticated downloader
        # instance; the handler no longer drives an interactive login flow.
        self.instagram_auth_manager = instagram_auth_manager
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        return get_config().instagram.url_patterns

    def _extract_metadata(self, url: str) -> JSONDict:
        """Extract Instagram-specific metadata from URL."""
        return {
            "type": self._detect_instagram_type(url),
            "shortcode": self._extract_shortcode(url),
        }

    def get_metadata(self, url: str) -> dict[str, str | bool | None]:
        """Get Instagram metadata for the URL."""
        return {
            "type": self._detect_instagram_type(url),
            "shortcode": self._extract_shortcode(url),
            # Auth is handled transparently by the downloader (session/cookie
            # import); private content still needs a logged-in browser session.
            "requires_auth": True,
        }

    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool:
        """Process Instagram download."""
        logger.info(f"[INSTAGRAM_HANDLER] Processing Instagram download: {url}")
        return True

    def get_ui_callback(self) -> UICallback:
        """Get the UI callback for Instagram URLs.

        Authentication is handled transparently by ``InstagramDownloader`` using
        saved sessions or cookies imported from the user's browser, so no
        interactive login dialog is triggered here. Public posts download
        immediately; gated content surfaces a clear, actionable message from the
        downloader when a session is unavailable.
        """
        logger.info("[INSTAGRAM_HANDLER] Getting UI callback")

        def instagram_callback(url: str, ui_context: UIContextProtocol) -> None:
            """Callback for handling Instagram URLs."""
            logger.info(f"[INSTAGRAM_HANDLER] Instagram callback called with URL: {url}")

            if not (download_callback := get_platform_callback(ui_context, "instagram")):
                error_msg = "No download callback found"
                logger.error(f"[INSTAGRAM_HANDLER] {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram Handler", "callback", error_msg, url
                    )
                return

            root = get_root(ui_context)

            def add_and_process() -> None:
                try:
                    logger.info(f"[INSTAGRAM_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[INSTAGRAM_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[INSTAGRAM_HANDLER] Error processing Instagram download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        self.error_handler.handle_exception(
                            e, "Processing Instagram download", "Instagram"
                        )

            schedule_on_main_thread(root, add_and_process, immediate=True)
            logger.info("[INSTAGRAM_HANDLER] Instagram download scheduled")

        logger.info("[INSTAGRAM_HANDLER] Returning Instagram callback")
        return instagram_callback

    def _detect_instagram_type(self, url: str) -> str:
        """Detect if URL is post, reel, story, etc."""
        type_markers = {
            "/p/": "post",
            "/reel/": "reel",
        }

        for marker, content_type in type_markers.items():
            if marker in url:
                return content_type

        return "unknown"

    def _extract_shortcode(self, url: str) -> str | None:
        """Extract shortcode from Instagram URL."""
        patterns = [
            r"/p/([\w-]+)",
            r"/reel/([\w-]+)",
        ]
        for pattern in patterns:
            if match := re.search(pattern, url):
                return match.group(1)
        return None
