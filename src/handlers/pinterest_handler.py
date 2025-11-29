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
class PinterestHandler(BaseHandler):
    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config, service_name="pinterest")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().pinterest.url_patterns

    def _extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract Pinterest-specific metadata from URL."""
        return {
            "type": self._detect_pinterest_type(url),
            "pin_id": self._extract_pin_id(url),
            "is_short_url": self._is_short_url(url),
        }

    def get_metadata(self, url: str) -> dict[str, Any]:
        """Get Pinterest metadata for the URL."""
        return {
            "type": self._detect_pinterest_type(url),
            "pin_id": self._extract_pin_id(url),
            "is_short_url": self._is_short_url(url),
            "requires_auth": False,  # Pinterest downloads usually work without auth
        }

    def process_download(self, url: str, options: dict[str, Any]) -> bool:
        """Process Pinterest download."""
        logger.info(f"[PINTEREST_HANDLER] Processing Pinterest download: {url}")
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for Pinterest URLs."""
        logger.info("[PINTEREST_HANDLER] Getting UI callback")

        def pinterest_callback(url: str, ui_context: Any):
            """Callback for handling Pinterest URLs."""
            logger.info(f"[PINTEREST_HANDLER] Pinterest callback called with URL: {url}")
            logger.info(f"[PINTEREST_HANDLER] UI context: {ui_context}")

            root = get_root(ui_context)

            logger.info(f"[PINTEREST_HANDLER] Root: {root}")

            download_callback = get_platform_callback(ui_context, "pinterest")
            if not download_callback:
                download_callback = get_platform_callback(ui_context, "generic")
                if not download_callback:
                    error_msg = "No download callback found"
                    logger.error(f"[PINTEREST_HANDLER] {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "Pinterest Handler", "callback", error_msg, url
                        )
                    return

            def process_pinterest_download():
                try:
                    logger.info(f"[PINTEREST_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[PINTEREST_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[PINTEREST_HANDLER] Error processing Pinterest download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        extract_error_context(e, "Pinterest", "download processing", url)
                        self.error_handler.handle_exception(
                            e, "Processing Pinterest download", "Pinterest"
                        )

            schedule_on_main_thread(root, process_pinterest_download, immediate=True)
            logger.info("[PINTEREST_HANDLER] Pinterest download scheduled")

        logger.info("[PINTEREST_HANDLER] Returning Pinterest callback")
        return pinterest_callback

    def _detect_pinterest_type(self, url: str) -> str:
        """Detect if URL is pin, board, etc."""
        if "/pin/" in url:
            return "pin"
        if "/board/" in url:
            return "board"
        if "pin.it" in url:
            return "short_pin"
        return "unknown"

    def _extract_pin_id(self, url: str) -> str | None:
        """Extract pin ID from Pinterest URL."""
        patterns = [
            r"/pin/(\d+)",
            r"pin\.it/([\w]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _is_short_url(self, url: str) -> bool:
        """Check if this is a pin.it short URL."""
        return "pin.it" in url
