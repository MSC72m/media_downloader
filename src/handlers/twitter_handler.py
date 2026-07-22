import re
from collections.abc import Mapping

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.core.type_defs import JSONDict, JSONValue
from src.services.detection.base_handler import BaseHandler
from src.services.detection.link_detector import (
    auto_register_handler,
)
from src.utils.logger import get_logger

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
