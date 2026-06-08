import re
from collections.abc import Mapping
from urllib.parse import unquote

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier, IMessageQueue, UIContextProtocol
from src.core.type_defs import JSONDict, JSONValue
from src.services.detection.base_handler import BaseHandler, UICallback
from src.services.detection.link_detector import (
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
class RadioJavanHandler(BaseHandler):
    def __init__(
        self,
        message_queue: IMessageQueue,
        error_handler: IErrorNotifier | None = None,
        config: AppConfig | None = None,
    ) -> None:
        resolved_config = config or get_config()
        super().__init__(message_queue, resolved_config, service_name="radiojavan")
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls) -> list[str]:
        """Get URL patterns for this handler."""
        return get_config().radiojavan.url_patterns

    def _extract_metadata(self, url: str) -> JSONDict:
        """Extract Radio Javan-specific metadata from URL."""
        return {
            "type": self._detect_radiojavan_type(url),
            "media_id": self._extract_media_id(url),
        }

    def get_metadata(self, url: str) -> JSONDict:
        """Get Radio Javan metadata for URL."""
        return {
            "type": self._detect_radiojavan_type(url),
            "media_id": self._extract_media_id(url),
            "requires_auth": False,
        }

    def process_download(self, url: str, options: Mapping[str, JSONValue]) -> bool:
        """Process Radio Javan download."""
        logger.info(f"[RADIOJAVAN_HANDLER] Processing Radio Javan download: {url}")
        return True

    def get_ui_callback(self) -> UICallback:
        """Get UI callback for Radio Javan URLs."""
        logger.info("[RADIOJAVAN_HANDLER] Getting UI callback")

        def radiojavan_callback(url: str, ui_context: UIContextProtocol) -> None:
            """Callback for handling Radio Javan URLs."""
            logger.info(f"[RADIOJAVAN_HANDLER] Radio Javan callback called with URL: {url}")

            root = get_root(ui_context)

            if not (download_callback := get_platform_callback(ui_context, "radiojavan")) and not (
                download_callback := get_platform_callback(ui_context, "generic")
            ):
                error_msg = "No download callback found"
                logger.error(f"[RADIOJAVAN_HANDLER] {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Radio Javan Handler", "callback", error_msg, url
                    )
                return

            def process_radiojavan_download() -> None:
                try:
                    logger.info(f"[RADIOJAVAN_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[RADIOJAVAN_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[RADIOJAVAN_HANDLER] Error processing Radio Javan download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        self.error_handler.handle_exception(
                            e, "Processing Radio Javan download", "Radio Javan"
                        )

            schedule_on_main_thread(root, process_radiojavan_download, immediate=True)
            logger.info("[RADIOJAVAN_HANDLER] Radio Javan download scheduled")

        logger.info("[RADIOJAVAN_HANDLER] Returning Radio Javan callback")
        return radiojavan_callback

    def _detect_radiojavan_type(self, url: str) -> str:
        """Detect if URL is song, video, artist page, etc."""
        if "/mp3/" in url or "/song/" in url:
            return "mp3"
        if "/mp4/" in url:
            return "mp4"
        if "/artist/" in url:
            return "artist"
        if "rj.app" in url.lower():
            return "short_url"
        return "unknown"

    def _extract_media_id(self, url: str) -> str | None:
        """Extract media ID from Radio Javan URL."""
        patterns = [
            r"/mp3/([\w%-]+)",
            r"/mp4/([\w%-]+)",
            r"/song/([\w%-]+)",
            r"rj\.app/([\w%-]+)",
        ]
        for pattern in patterns:
            if match := re.search(pattern, url):
                return unquote(match.group(1))
        return None
