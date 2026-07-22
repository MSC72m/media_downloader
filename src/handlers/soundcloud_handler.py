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
class SoundCloudHandler(BaseHandler):
    def __init__(
        self,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        super().__init__(message_queue, resolved_config, service_name="soundcloud")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        return get_config().soundcloud.url_patterns

    def _extract_metadata(self, url: str) -> JSONDict:
        """Extract SoundCloud-specific metadata from URL."""
        return {
            "type": self._detect_soundcloud_type(url),
            "username": self._extract_username(url),
            "track_slug": self._extract_track_slug(url),
        }

    def get_metadata(self, url: str) -> JSONDict:
        """Get SoundCloud metadata for the URL."""
        return {
            "type": self._detect_soundcloud_type(url),
            "username": self._extract_username(url),
            "track_slug": self._extract_track_slug(url),
            "requires_auth": False,  # SoundCloud downloads usually work without auth
        }

    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool:
        """Process SoundCloud download."""
        logger.info(f"[SOUNDCLOUD_HANDLER] Processing SoundCloud download: {url}")
        return True

    def _detect_soundcloud_type(self, url: str) -> str:
        """Detect if URL is track, playlist/set, or user profile."""
        if "/sets/" in url:
            return "playlist"
        if re.search(r"soundcloud\.com/[\w-]+/[\w-]+", url):
            return "track"
        if re.search(r"soundcloud\.com/[\w-]+/?$", url):
            return "user"
        return "unknown"

    def _extract_username(self, url: str) -> str | None:
        """Extract username from SoundCloud URL."""
        match = re.search(r"soundcloud\.com/([\w-]+)", url)
        return match.group(1) if match else None

    def _extract_track_slug(self, url: str) -> str | None:
        """Extract track slug from SoundCloud URL."""
        match = re.search(r"soundcloud\.com/[\w-]+/([\w-]+)", url)
        return match.group(1) if match else None
