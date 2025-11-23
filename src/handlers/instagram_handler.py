"""Instagram link handler implementation."""

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
class InstagramHandler(LinkHandlerInterface):
    """Handler for Instagram URLs."""

    INSTAGRAM_PATTERNS = [
        r"^https?://(?:www\.)?instagram\.com/p/[\w-]+",
        r"^https?://(?:www\.)?instagram\.com/reel/[\w-]+",
        r"^https?://(?:www\.)?instagram\.com/stories/[\w-]+",
        r"^https?://(?:www\.)?instagram\.com/tv/[\w-]+",
    ]

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return cls.INSTAGRAM_PATTERNS

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is an Instagram URL."""
        for pattern in self.INSTAGRAM_PATTERNS:
            if re.match(pattern, url):
                return DetectionResult(
                    service_type="instagram",
                    confidence=1.0,
                    metadata={
                        "type": self._detect_instagram_type(url),
                        "shortcode": self._extract_shortcode(url),
                    },
                )
        return DetectionResult(service_type="unknown", confidence=0.0)

    def get_metadata(self, url: str) -> Dict[str, str | None | bool]:
        """Get Instagram metadata for the URL."""
        # This would integrate with Instagram metadata service
        return {
            "type": self._detect_instagram_type(url),
            "shortcode": self._extract_shortcode(url),
            "requires_auth": True,
        }

    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process Instagram download."""
        print(f"Processing Instagram download: {url}")
        # Actual Instagram download logic would go here
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for Instagram URLs."""
        logger.info("[INSTAGRAM_HANDLER] Getting UI callback")

        def instagram_callback(url: str, ui_context: Any):
            """Callback for handling Instagram URLs."""
            logger.info(
                f"[INSTAGRAM_HANDLER] Instagram callback called with URL: {url}"
            )
            logger.info(f"[INSTAGRAM_HANDLER] UI context: {ui_context}")

            # Get root using type-safe helper
            root = get_root(ui_context)

            # Get download callback using type-safe helper
            download_callback = get_platform_callback(ui_context, "instagram")
            if not download_callback:
                # Try generic fallback
                download_callback = get_platform_callback(ui_context, "generic")
                if not download_callback:
                    logger.error("[INSTAGRAM_HANDLER] No download callback found")
                    return

            # Call the platform download method which will show the dialog (or fallback)
            def process_instagram_download():
                try:
                    logger.info(
                        f"[INSTAGRAM_HANDLER] Calling download callback for: {url}"
                    )
                    # Platform download methods expect URL string
                    download_callback(url)
                    logger.info("[INSTAGRAM_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[INSTAGRAM_HANDLER] Error processing Instagram download: {e}",
                        exc_info=True,
                    )

            # Schedule on main thread
            schedule_on_main_thread(root, process_instagram_download, immediate=True)
            logger.info("[INSTAGRAM_HANDLER] Instagram download scheduled")

        logger.info("[INSTAGRAM_HANDLER] Returning Instagram callback")
        return instagram_callback

    def _detect_instagram_type(self, url: str) -> str:
        """Detect if URL is post, reel, story, etc."""
        type_markers = {
            "/p/": "post",
            "/reel/": "reel",
            "/stories/": "story",
            "/tv/": "tv",
        }

        for marker, content_type in type_markers.items():
            if marker in url:
                return content_type

        return "unknown"

    def _extract_shortcode(self, url: str) -> Optional[str]:
        """Extract shortcode from Instagram URL."""
        patterns = [
            r"/p/([\w-]+)",
            r"/reel/([\w-]+)",
            r"/stories/[\w-]+/([\w-]+)",
            r"/tv/([\w-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
