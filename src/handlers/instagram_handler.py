"""Instagram link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from ..services.detection.link_detector import (
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)


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

    def get_metadata(self, url: str) -> Dict[str, Any]:
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

        def instagram_callback(url: str, ui_context: Any):
            """Callback for handling Instagram URLs."""
            # Show Instagram login or directly process
            if hasattr(ui_context, "handle_instagram_login"):
                ui_context.handle_instagram_login()

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
