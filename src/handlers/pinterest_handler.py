"""Pinterest link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from src.core.interfaces import IErrorHandler
from src.services.detection.link_detector import (
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_platform_callback,
    get_root,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class PinterestHandler(LinkHandlerInterface):
    """Handler for Pinterest URLs."""

    def __init__(self, error_handler: Optional[IErrorHandler] = None):
        """Initialize Pinterest handler.

        Args:
            error_handler: Optional error handler for user notifications
        """
        self.error_handler = error_handler

    PINTEREST_PATTERNS = [
        r"^https?://(?:www\.)?pinterest\.com/pin/[\d]+",
        r"^https?://(?:www\.)?pinterest\.com/[\w]+/[\w-]+/[\d]+",
        r"^https?://(?:www\.)?pin\.it/[\w]+",
        r"^https?://(?:www\.)?pinterest\.com\.au/pin/[\d]+",
        r"^https?://(?:www\.)?pinterest\.ca/pin/[\d]+",
        r"^https?://(?:www\.)?pinterest\.co\.uk/pin/[\d]+",
        r"^https?://(?:www\.)?pinterest\.de/pin/[\d]+",
        r"^https?://(?:www\.)?pinterest\.fr/pin/[\d]+",
    ]

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return cls.PINTEREST_PATTERNS

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is a Pinterest URL."""
        logger.debug(f"[PINTEREST_HANDLER] Testing if can handle URL: {url}")

        for pattern in self.PINTEREST_PATTERNS:
            if re.match(pattern, url):
                logger.info(f"[PINTEREST_HANDLER] URL matches pattern: {pattern}")
                result = DetectionResult(
                    service_type="pinterest",
                    confidence=1.0,
                    metadata={
                        "type": self._detect_pinterest_type(url),
                        "pin_id": self._extract_pin_id(url),
                        "is_short_url": self._is_short_url(url),
                    },
                )
                logger.info(
                    f"[PINTEREST_HANDLER] Can handle URL with confidence: {result.confidence}"
                )
                logger.debug(
                    f"[PINTEREST_HANDLER] Detection metadata: {result.metadata}"
                )
                return result

        logger.debug("[PINTEREST_HANDLER] URL does not match any pattern")
        return DetectionResult(service_type="unknown", confidence=0.0)

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get Pinterest metadata for the URL."""
        return {
            "type": self._detect_pinterest_type(url),
            "pin_id": self._extract_pin_id(url),
            "is_short_url": self._is_short_url(url),
            "requires_auth": False,  # Pinterest downloads usually work without auth
        }

    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process Pinterest download."""
        logger.info(f"[PINTEREST_HANDLER] Processing Pinterest download: {url}")
        # Actual Pinterest download logic would go here
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for Pinterest URLs."""
        logger.info("[PINTEREST_HANDLER] Getting UI callback")

        def pinterest_callback(url: str, ui_context: Any):
            """Callback for handling Pinterest URLs."""
            logger.info(
                f"[PINTEREST_HANDLER] Pinterest callback called with URL: {url}"
            )
            logger.info(f"[PINTEREST_HANDLER] UI context: {ui_context}")

            # Get root using type-safe helper
            root = get_root(ui_context)

            logger.info(f"[PINTEREST_HANDLER] Root: {root}")

            download_callback = get_platform_callback(ui_context, "pinterest")
            if not download_callback:
                download_callback = get_platform_callback(ui_context, "generic")
                if not download_callback:
                    error_msg = "No download callback found"
                    logger.error(f"[PINTEREST_HANDLER] {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure("Pinterest Handler", "callback", error_msg, url)
                    return

            # Call the platform download method which will show the dialog (or fallback)
            def process_pinterest_download():
                try:
                    logger.info(
                        f"[PINTEREST_HANDLER] Calling download callback for: {url}"
                    )
                    # Platform download methods expect URL string
                    download_callback(url)
                    logger.info("[PINTEREST_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(f"[PINTEREST_HANDLER] Error processing Pinterest download: {e}", exc_info=True)
                    if self.error_handler:
                        self.error_handler.handle_exception(e, "Processing Pinterest download", "Pinterest")

            # Schedule on main thread
            schedule_on_main_thread(root, process_pinterest_download, immediate=True)
            logger.info("[PINTEREST_HANDLER] Pinterest download scheduled")

        logger.info("[PINTEREST_HANDLER] Returning Pinterest callback")
        return pinterest_callback

    def _detect_pinterest_type(self, url: str) -> str:
        """Detect if URL is pin, board, etc."""
        if "/pin/" in url:
            return "pin"
        elif "/board/" in url:
            return "board"
        elif "pin.it" in url:
            return "short_pin"
        return "unknown"

    def _extract_pin_id(self, url: str) -> Optional[str]:
        """Extract pin ID from Pinterest URL."""
        # Match pin ID in various URL formats
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
