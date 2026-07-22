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
class PinterestHandler(BaseHandler):
    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        super().__init__(message_queue, resolved_config, service_name="pinterest")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        return get_config().pinterest.url_patterns

    def _extract_metadata(self, url: str) -> JSONDict:
        """Extract Pinterest-specific metadata from URL."""
        return {
            "type": self._detect_pinterest_type(url),
            "pin_id": self._extract_pin_id(url),
            "is_short_url": self._is_short_url(url),
        }

    def get_metadata(self, url: str) -> JSONDict:
        """Get Pinterest metadata for the URL."""
        return {
            "type": self._detect_pinterest_type(url),
            "pin_id": self._extract_pin_id(url),
            "is_short_url": self._is_short_url(url),
            "requires_auth": False,  # Pinterest downloads usually work without auth
        }

    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool:
        """Process Pinterest download."""
        logger.info(f"[PINTEREST_HANDLER] Processing Pinterest download: {url}")
        return True

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
            if match := re.search(pattern, url):
                return match.group(1)
        return None

    def _is_short_url(self, url: str) -> bool:
        """Check if this is a pin.it short URL."""
        return "pin.it" in url
