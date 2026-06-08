import re
from collections.abc import Mapping

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier, IMessageQueue, UIContextProtocol
from src.core.type_defs import JSONDict, JSONValue
from src.services.detection.base_handler import BaseHandler, UICallback
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
class TwitterHandler(BaseHandler):
    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        super().__init__(message_queue, resolved_config, service_name="twitter")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        return get_config().twitter.url_patterns

    def _extract_metadata(self, url: str) -> JSONDict:
        """Extract Twitter-specific metadata from URL."""
        return {
            "type": self._detect_twitter_type(url),
            "tweet_id": self._extract_tweet_id(url),
            "username": self._extract_username(url),
        }

    def get_metadata(self, url: str) -> JSONDict:
        """Get Twitter metadata for the URL."""
        return {
            "type": self._detect_twitter_type(url),
            "tweet_id": self._extract_tweet_id(url),
            "username": self._extract_username(url),
            "requires_auth": False,  # Twitter downloads usually work without auth
        }

    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool:
        """Process Twitter download."""
        logger.info(f"[TWITTER_HANDLER] Processing Twitter download: {url}")
        return True

    def get_ui_callback(self) -> UICallback:
        """Get the UI callback for Twitter URLs."""
        logger.info("[TWITTER_HANDLER] Getting UI callback")

        def twitter_callback(url: str, ui_context: UIContextProtocol) -> None:
            """Callback for handling Twitter URLs."""
            logger.info(f"[TWITTER_HANDLER] Twitter callback called with URL: {url}")
            logger.info(f"[TWITTER_HANDLER] UI context: {ui_context}")

            root = get_root(ui_context)

            logger.info(f"[TWITTER_HANDLER] Root: {root}")

            if not (download_callback := get_platform_callback(ui_context, "twitter")) and not (
                download_callback := get_platform_callback(ui_context, "generic")
            ):
                error_msg = "No download callback found"
                logger.error(f"[TWITTER_HANDLER] {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Twitter Handler", "callback", error_msg, url
                    )
                return

            def process_twitter_download() -> None:
                try:
                    logger.info(f"[TWITTER_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[TWITTER_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[TWITTER_HANDLER] Error processing Twitter download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        extract_error_context(e, "Twitter", "download processing", url)
                        self.error_handler.handle_exception(
                            e, "Processing Twitter download", "Twitter"
                        )

            schedule_on_main_thread(root, process_twitter_download, immediate=True)
            logger.info("[TWITTER_HANDLER] Twitter download scheduled")

        logger.info("[TWITTER_HANDLER] Returning Twitter callback")
        return twitter_callback

    def _detect_twitter_type(self, url: str) -> str:
        """Detect if URL is tweet, space, etc."""
        if "/spaces/" in url or "/i/spaces/" in url:
            return "space"
        if "/status/" in url:
            return "tweet"
        return "unknown"

    def _extract_tweet_id(self, url: str) -> str | None:
        """Extract tweet ID from Twitter URL."""
        match = re.search(r"/status/(\d+)", url)
        return match.group(1) if match else None

    def _extract_username(self, url: str) -> str | None:
        """Extract username from Twitter URL."""
        match = re.search(r"(?:twitter\.com|x\.com)/(\w+)/", url)
        return match.group(1) if match else None
