import re
from collections.abc import Callable
from typing import Any

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.detection.base_handler import BaseHandler
from src.services.detection.link_detector import (
    auto_register_handler,
)
from src.utils import type_helpers
from src.utils.logger import get_logger

logger = get_logger(__name__)


@auto_register_handler
class TikTokHandler(BaseHandler):
    def __init__(
        self,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config, service_name="tiktok")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().tiktok.url_patterns

    def _extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract TikTok-specific metadata from URL."""
        return {
            "type": self._detect_tiktok_type(url),
            "video_id": self._extract_video_id(url),
        }

    def get_metadata(self, url: str) -> dict[str, Any]:
        """Get TikTok metadata for URL."""
        return {
            "type": self._detect_tiktok_type(url),
            "video_id": self._extract_video_id(url),
            "requires_auth": False,
        }

    def process_download(self, url: str, options: dict[str, Any]) -> bool:
        """Process TikTok download."""
        logger.info(f"[TIKTOK_HANDLER] Processing TikTok download: {url}")
        return True

    def get_ui_callback(self) -> Callable:
        """Get UI callback for TikTok URLs."""
        logger.info("[TIKTOK_HANDLER] Getting UI callback")

        def tiktok_callback(url: str, ui_context: Any):
            """Callback for handling TikTok URLs."""
            logger.info(f"[TIKTOK_HANDLER] TikTok callback called with URL: {url}")

            root = type_helpers.get_root(ui_context)

            if not (
                download_callback := type_helpers.get_platform_callback(ui_context, "tiktok")
            ) and not (
                download_callback := type_helpers.get_platform_callback(ui_context, "generic")
            ):
                error_msg = "No download callback found"
                logger.error(f"[TIKTOK_HANDLER] {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "TikTok Handler", "callback", error_msg, url
                    )
                return

            def process_tiktok_download():
                try:
                    logger.info(f"[TIKTOK_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[TIKTOK_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[TIKTOK_HANDLER] Error processing TikTok download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        self.error_handler.handle_exception(
                            e, "Processing TikTok download", "TikTok"
                        )

            type_helpers.schedule_on_main_thread(root, process_tiktok_download, immediate=True)
            logger.info("[TIKTOK_HANDLER] TikTok download scheduled")

        logger.info("[TIKTOK_HANDLER] Returning TikTok callback")
        return tiktok_callback

    def _detect_tiktok_type(self, url: str) -> str:
        """Detect if URL is video, user profile, etc."""
        if "/video/" in url:
            return "video"
        if "/t/" in url:
            return "user"
        if "@tiktok.com" in url.lower():
            return "user_link"
        return "unknown"

    def _extract_video_id(self, url: str) -> str | None:
        """Extract video ID from TikTok URL."""
        patterns = [
            r"/video/(\d+)",
            r"/v/([\w-]+)",
        ]
        for pattern in patterns:
            if match := re.search(pattern, url):
                return match.group(1)
        return None
