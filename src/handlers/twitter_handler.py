"""Twitter link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from src.core.config import get_config, AppConfig
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.detection.link_detector import (
    DetectionResult,
    auto_register_handler,
)
from src.services.detection.base_handler import BaseHandler
from src.utils.error_helpers import extract_error_context
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_platform_callback,
    get_root,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class TwitterHandler(BaseHandler):
    def __init__(self, error_handler: Optional[IErrorNotifier] = None, message_queue: Optional[IMessageQueue] = None, config: AppConfig = get_config()):
        super().__init__(message_queue, config, service_name="twitter")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().twitter.url_patterns

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is a Twitter/X URL."""
        logger.debug(f"[TWITTER_HANDLER] Testing if can handle URL: {url}")

        for pattern in self.config.twitter.url_patterns:
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

            # Get root using type-safe helper
            root = get_root(ui_context)

            logger.info(f"[TWITTER_HANDLER] Root: {root}")

            download_callback = get_platform_callback(ui_context, "twitter")
            if not download_callback:
                download_callback = get_platform_callback(ui_context, "generic")
                if not download_callback:
                    error_msg = "No download callback found"
                    logger.error(f"[TWITTER_HANDLER] {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure("Twitter Handler", "callback", error_msg, url)
                    return

            # Call the platform download method which will show the dialog (or fallback)
            def process_twitter_download():
                try:
                    logger.info(
                        f"[TWITTER_HANDLER] Calling download callback for: {url}"
                    )
                    # Platform download methods expect URL string
                    download_callback(url)
                    logger.info("[TWITTER_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(f"[TWITTER_HANDLER] Error processing Twitter download: {e}", exc_info=True)
                    if self.error_handler:
                        error_context = extract_error_context(e, "Twitter", "download processing", url)
                        self.error_handler.handle_exception(e, "Processing Twitter download", "Twitter")

            # Schedule on main thread
            schedule_on_main_thread(root, process_twitter_download, immediate=True)
            logger.info("[TWITTER_HANDLER] Twitter download scheduled")

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
