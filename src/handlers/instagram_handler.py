import re
from collections.abc import Callable
from typing import Any

from src.core.config import AppConfig, get_config
from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.enums.message_level import MessageLevel
from src.core.enums.service_type import ServiceType
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.core.models import Download, DownloadStatus
from src.services.detection.base_handler import BaseHandler
from src.services.detection.link_detector import (
    auto_register_handler,
)
from src.services.events.queue import Message
from src.services.instagram.auth_manager import InstagramAuthManager
from src.utils.error_helpers import extract_error_context
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    get_platform_callback,
    get_root,
    get_ui_context,
    schedule_on_main_thread,
)

logger = get_logger(__name__)


@auto_register_handler
class InstagramHandler(BaseHandler):
    def __init__(
        self,
        instagram_auth_manager: InstagramAuthManager,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config, service_name="instagram")
        self.instagram_auth_manager = instagram_auth_manager
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().instagram.url_patterns

    def _extract_metadata(self, url: str) -> dict[str, Any]:
        """Extract Instagram-specific metadata from URL."""
        return {
            "type": self._detect_instagram_type(url),
            "shortcode": self._extract_shortcode(url),
        }

    def get_metadata(self, url: str) -> dict[str, str | None | bool]:
        """Get Instagram metadata for the URL."""
        return {
            "type": self._detect_instagram_type(url),
            "shortcode": self._extract_shortcode(url),
            "requires_auth": True,
        }

    def process_download(self, url: str, options: dict[str, Any]) -> bool:
        """Process Instagram download."""
        logger.info(f"[INSTAGRAM_HANDLER] Processing Instagram download: {url}")
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for Instagram URLs."""
        logger.info("[INSTAGRAM_HANDLER] Getting UI callback")

        def instagram_callback(url: str, ui_context: Any):
            """Callback for handling Instagram URLs."""
            logger.info(f"[INSTAGRAM_HANDLER] Instagram callback called with URL: {url}")

            download_callback = get_platform_callback(ui_context, "instagram")
            if not download_callback:
                error_msg = "No download callback found"
                logger.error(f"[INSTAGRAM_HANDLER] {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram Handler", "callback", error_msg, url
                    )
                return

            if self.instagram_auth_manager.is_authenticating():
                self.notifier.notify_user("authenticating")
                return

            root = get_root(ui_context)

            ctx = get_ui_context(ui_context)
            if not ctx:
                logger.error("[INSTAGRAM_HANDLER] Could not get UI context")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram Handler",
                        "context",
                        "Could not access UI context",
                        url,
                    )
                return

            logger.info("[INSTAGRAM_HANDLER] Adding Instagram URL to downloads immediately")
            download_name = f"Instagram - {url[:50]}..." if len(url) > 50 else f"Instagram - {url}"
            download = Download(
                name=download_name,
                url=url,
                status=DownloadStatus.PENDING,
                service_type=ServiceType.INSTAGRAM,
            )

            download_index_ref = {"index": None}

            def add_download_to_list():
                try:
                    if hasattr(ctx, "downloads") and hasattr(ctx.downloads, "add_download"):
                        ctx.downloads.add_download(download)
                        logger.info("[INSTAGRAM_HANDLER] Download added to list directly")

                        if hasattr(ctx.downloads, "get_downloads"):
                            downloads = ctx.downloads.get_downloads()
                            for idx, d in enumerate(downloads):
                                if d.url == url:
                                    download_index_ref["index"] = idx
                                    logger.info(
                                        f"[INSTAGRAM_HANDLER] Tracked download at index: {idx}"
                                    )
                                    break
                    else:
                        logger.warning(
                            "[INSTAGRAM_HANDLER] Downloads coordinator not available, using callback"
                        )
                        download_callback(url)
                except Exception as e:
                    logger.error(f"[INSTAGRAM_HANDLER] Error adding download: {e}", exc_info=True)
                    if self.error_handler:
                        self.error_handler.handle_exception(
                            e, "Adding Instagram download", "Instagram Handler"
                        )

            schedule_on_main_thread(root, add_download_to_list, immediate=True)

            if not self.instagram_auth_manager.is_authenticated():
                logger.info("[INSTAGRAM_HANDLER] Instagram not authenticated, triggering auth flow")

                if not hasattr(ctx, "platform_dialogs"):
                    logger.error(
                        "[INSTAGRAM_HANDLER] Could not get platform dialog coordinator from UI context"
                    )
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "Instagram Handler",
                            "authentication",
                            "Could not access authentication dialog",
                            url,
                        )
                    return

                platform_coordinator = ctx.platform_dialogs

                def on_auth_complete(status):
                    """Callback after authentication completes.

                    Args:
                        status: InstagramAuthStatus indicating authentication result
                    """
                    logger.info(f"[INSTAGRAM_HANDLER] Auth callback received status: {status}")

                    if (
                        status == InstagramAuthStatus.AUTHENTICATED
                        and self.instagram_auth_manager.is_authenticated()
                    ):
                        logger.info(
                            "[INSTAGRAM_HANDLER] Authentication successful, download already added"
                        )
                    else:
                        logger.warning(
                            f"[INSTAGRAM_HANDLER] Authentication failed or cancelled: {status}"
                        )
                        if download_index_ref["index"] is not None and hasattr(ctx, "downloads"):

                            def remove_download():
                                try:
                                    ctx.downloads.remove_downloads([download_index_ref["index"]])
                                    logger.info(
                                        f"[INSTAGRAM_HANDLER] Removed download at index {download_index_ref['index']} due to auth failure"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"[INSTAGRAM_HANDLER] Error removing download: {e}",
                                        exc_info=True,
                                    )

                            schedule_on_main_thread(root, remove_download, immediate=True)

                        if self.message_queue:
                            error_msg = "Instagram authentication failed. Please try again."
                            self.message_queue.add_message(
                                Message(
                                    text=error_msg,
                                    level=MessageLevel.ERROR,
                                    title="Instagram Authentication Failed",
                                )
                            )

                platform_coordinator.authenticate_instagram(root, on_auth_complete)
                return

            def process_instagram_download():
                try:
                    logger.info(f"[INSTAGRAM_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[INSTAGRAM_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(
                        f"[INSTAGRAM_HANDLER] Error processing Instagram download: {e}",
                        exc_info=True,
                    )
                    if self.error_handler:
                        extract_error_context(e, "Instagram", "download processing", url)
                        self.error_handler.handle_exception(
                            e, "Processing Instagram download", "Instagram"
                        )

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

    def _extract_shortcode(self, url: str) -> str | None:
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
