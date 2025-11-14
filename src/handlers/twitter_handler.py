"""Twitter/X link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from src.services.detection.link_detector import (
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


@auto_register_handler
class TwitterHandler(LinkHandlerInterface):
    """Handler for Twitter/X URLs."""

    # Twitter/X URL patterns
    TWITTER_PATTERNS = [
        r"^https?://(?:www\.)?twitter\.com/[\w]+/status/[\d]+",
        r"^https?://(?:www\.)?x\.com/[\w]+/status/[\d]+",
        r"^https?://(?:www\.)?twitter\.com/i/spaces/[\w]+",
        r"^https?://(?:www\.)?x\.com/i/spaces/[\w]+",
        r"^https?://(?:mobile\.)?twitter\.com/[\w]+/status/[\d]+",
        r"^https?://(?:mobile\.)?x\.com/[\w]+/status/[\d]+",
    ]

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return cls.TWITTER_PATTERNS

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is a Twitter/X URL."""
        logger.debug(f"[TWITTER_HANDLER] Testing if can handle URL: {url}")

        for pattern in self.TWITTER_PATTERNS:
            if re.match(pattern, url):
                logger.info(f"[TWITTER_HANDLER] URL matches pattern: {pattern}")
                result = DetectionResult(
                    service_type="twitter",
                    confidence=1.0,
                    metadata={
                        "type": self._detect_twitter_type(url),
                        "tweet_id": self._extract_tweet_id(url),
                        "username": self._extract_username(url),
                    },
                )
                logger.info(
                    f"[TWITTER_HANDLER] Can handle URL with confidence: {result.confidence}"
                )
                logger.debug(f"[TWITTER_HANDLER] Detection metadata: {result.metadata}")
                return result

        logger.debug("[TWITTER_HANDLER] URL does not match any pattern")
        return DetectionResult(service_type="unknown", confidence=0.0)

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get Twitter metadata for the URL."""
        return {
            "type": self._detect_twitter_type(url),
            "tweet_id": self._extract_tweet_id(url),
            "username": self._extract_username(url),
            "requires_auth": False,  # Twitter downloads usually work without auth
        }

    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process Twitter download."""
        logger.info(f"[TWITTER_HANDLER] Processing Twitter download: {url}")
        # Actual Twitter download logic would go here
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for Twitter URLs."""
        logger.info("[TWITTER_HANDLER] Getting UI callback")

        def twitter_callback(url: str, ui_context: Any):
            """Callback for handling Twitter URLs."""
            logger.info(f"[TWITTER_HANDLER] Twitter callback called with URL: {url}")
            logger.info(f"[TWITTER_HANDLER] UI context: {ui_context}")
            logger.info(f"[TWITTER_HANDLER] UI context type: {type(ui_context)}")

            # Get container and root from ui_context
            container = (
                ui_context.container
                if hasattr(ui_context, "container")
                else ui_context.event_coordinator.container
                if hasattr(ui_context, "event_coordinator")
                else None
            )
            root = (
                ui_context.root
                if hasattr(ui_context, "root")
                else ui_context.event_coordinator.root
                if hasattr(ui_context, "event_coordinator")
                else ui_context
            )

            logger.info(f"[TWITTER_HANDLER] Container: {container}")
            logger.info(f"[TWITTER_HANDLER] Root: {root}")

            # Get download callback
            download_callback = None
            if hasattr(ui_context, "handle_twitter_download"):
                download_callback = ui_context.handle_twitter_download
                logger.info(
                    "[TWITTER_HANDLER] Using ui_context handle_twitter_download callback"
                )
            elif hasattr(ui_context, "event_coordinator"):
                download_callback = ui_context.event_coordinator.handle_twitter_download
                logger.info(
                    "[TWITTER_HANDLER] Using event_coordinator handle_twitter_download callback"
                )

            if not download_callback:
                logger.error("[TWITTER_HANDLER] No download callback found")
                # Fallback: try to create a generic download
                if hasattr(ui_context, "handle_generic_download"):
                    download_callback = ui_context.handle_generic_download
                elif hasattr(ui_context, "event_coordinator") and hasattr(
                    ui_context.event_coordinator, "handle_generic_download"
                ):
                    download_callback = (
                        ui_context.event_coordinator.handle_generic_download
                    )
                else:
                    logger.error(
                        "[TWITTER_HANDLER] No fallback download callback found"
                    )
                    return

            # Create download configuration
            metadata = self.get_metadata(url)

            def process_twitter_download():
                try:
                    logger.info(f"[TWITTER_HANDLER] Processing download for: {url}")

                    # Create download configuration
                    download_config = {
                        "url": url,
                        "service_type": "twitter",
                        "metadata": metadata,
                        "quality": "best",  # Default quality
                        "format": "video",  # Twitter typically has videos
                    }

                    # Call the download callback
                    download_callback(download_config)
                    logger.info("[TWITTER_HANDLER] Download callback executed")

                except Exception as e:
                    logger.error(
                        f"[TWITTER_HANDLER] Error processing Twitter download: {e}",
                        exc_info=True,
                    )

            # Schedule on main thread
            if hasattr(root, "after"):
                root.after(0, process_twitter_download)
                logger.info("[TWITTER_HANDLER] Twitter download scheduled")
            else:
                process_twitter_download()

        logger.info("[TWITTER_HANDLER] Returning Twitter callback")
        return twitter_callback

    def _detect_twitter_type(self, url: str) -> str:
        """Detect if URL is tweet, space, etc."""
        if "/spaces/" in url or "/i/spaces/" in url:
            return "space"
        elif "/status/" in url:
            return "tweet"
        return "unknown"

    def _extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from Twitter URL."""
        match = re.search(r"/status/(\d+)", url)
        return match.group(1) if match else None

    def _extract_username(self, url: str) -> Optional[str]:
        """Extract username from Twitter URL."""
        match = re.search(r"(?:twitter\.com|x\.com)/(\w+)/", url)
        return match.group(1) if match else None
