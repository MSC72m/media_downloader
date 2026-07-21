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
class TikTokHandler(BaseHandler):
    def __init__(
        self,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        super().__init__(message_queue, resolved_config, service_name="tiktok")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        return get_config().tiktok.url_patterns

    def _extract_metadata(self, url: str) -> JSONDict:
        """Extract TikTok-specific metadata from URL."""
        return {
            "type": self._detect_tiktok_type(url),
            "video_id": self._extract_video_id(url),
        }

    def get_metadata(self, url: str) -> JSONDict:
        """Get TikTok metadata for URL."""
        return {
            "type": self._detect_tiktok_type(url),
            "video_id": self._extract_video_id(url),
            "requires_auth": False,
        }

    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool:
        """Process TikTok download."""
        logger.info(f"[TIKTOK_HANDLER] Processing TikTok download: {url}")
        return True

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
