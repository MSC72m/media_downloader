"""Instagram link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from src.core.config import get_config, AppConfig
from src.core.base.base_handler import BaseHandler
from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.core.enums.message_level import MessageLevel
from src.core.enums.service_type import ServiceType
from src.core.models import Download, DownloadStatus
from src.interfaces.service_interfaces import IErrorHandler
from src.services.events.queue import Message
from src.services.instagram.auth_manager import InstagramAuthManager
from src.services.detection.link_detector import (
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)
from src.ui.components.loading_dialog import LoadingDialog
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
class InstagramHandler(BaseHandler, LinkHandlerInterface):
    """Handler for Instagram URLs."""

    def __init__(
        self,
        instagram_auth_manager: InstagramAuthManager,
        error_handler: Optional[IErrorHandler] = None,
        message_queue=None,
        config: AppConfig = get_config(),
    ):
        """Initialize Instagram handler.

        Args:
            instagram_auth_manager: Instagram authentication manager
            error_handler: Optional error handler for user notifications
            message_queue: Optional message queue for notifications
            config: AppConfig instance (defaults to get_config() if None)
        """
        super().__init__(message_queue, config)
        self.instagram_auth_manager = instagram_auth_manager
        self.error_handler = error_handler

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return get_config().instagram.url_patterns

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is an Instagram URL."""
        for pattern in self.config.instagram.url_patterns:
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

    def get_metadata(self, url: str) -> Dict[str, str | None | bool]:
        """Get Instagram metadata for the URL."""
        # This would integrate with Instagram metadata service
        return {
            "type": self._detect_instagram_type(url),
            "shortcode": self._extract_shortcode(url),
            "requires_auth": True,
        }

    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process Instagram download."""
        logger.info(f"[INSTAGRAM_HANDLER] Processing Instagram download: {url}")
        # Actual Instagram download logic would go here
        return True

    def _get_notification_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get Instagram-specific notification templates."""
        base_templates = super()._get_notification_templates()
        instagram_templates = {
            "authenticating": {
                "text": "Instagram authentication is in progress. Please wait a moment and try again.",
                "title": "Instagram Authentication",
                "level": "INFO",
            },
            "authentication_required": {
                "text": "Instagram authentication is required to download content.",
                "title": "Instagram Authentication Required",
                "level": "INFO",
            },
        }
        base_templates.update(instagram_templates)
        return base_templates

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
                    self.error_handler.handle_service_failure("Instagram Handler", "callback", error_msg, url)
                return

            # Check authentication state (polymorphic - no if/else chains)
            if self.instagram_auth_manager.is_authenticating():
                self.notify_user("authenticating")
                return

            root = get_root(ui_context)

            # Get UI context to access downloads coordinator
            ctx = get_ui_context(ui_context)
            if not ctx:
                logger.error("[INSTAGRAM_HANDLER] Could not get UI context")
                if self.error_handler:
                    self.error_handler.handle_service_failure("Instagram Handler", "context", "Could not access UI context", url)
                return

            # Add download immediately when Instagram URL is detected
            logger.info("[INSTAGRAM_HANDLER] Adding Instagram URL to downloads immediately")
            download_name = f"Instagram - {url[:50]}..." if len(url) > 50 else f"Instagram - {url}"
            download = Download(
                name=download_name,
                url=url,
                status=DownloadStatus.PENDING,
                service_type=ServiceType.INSTAGRAM
            )
            
            # Track download index for potential removal if auth fails
            download_index_ref = {"index": None}
            
            def add_download_to_list():
                try:
                    # Add download directly via downloads coordinator
                    if hasattr(ctx, 'downloads') and hasattr(ctx.downloads, 'add_download'):
                        ctx.downloads.add_download(download)
                        logger.info("[INSTAGRAM_HANDLER] Download added to list directly")
                        
                        # Find the index of the added download
                        if hasattr(ctx.downloads, 'get_downloads'):
                            downloads = ctx.downloads.get_downloads()
                            for idx, d in enumerate(downloads):
                                if d.url == url:
                                    download_index_ref["index"] = idx
                                    logger.info(f"[INSTAGRAM_HANDLER] Tracked download at index: {idx}")
                                    break
                    else:
                        # Fallback to callback if downloads coordinator not available
                        logger.warning("[INSTAGRAM_HANDLER] Downloads coordinator not available, using callback")
                        download_callback(url)
                except Exception as e:
                    logger.error(f"[INSTAGRAM_HANDLER] Error adding download: {e}", exc_info=True)
                    if self.error_handler:
                        self.error_handler.handle_exception(e, "Adding Instagram download", "Instagram Handler")
            
            schedule_on_main_thread(root, add_download_to_list, immediate=True)

            # Check if authenticated, if not trigger authentication flow
            if not self.instagram_auth_manager.is_authenticated():
                logger.info("[INSTAGRAM_HANDLER] Instagram not authenticated, triggering auth flow")
                
                if not hasattr(ctx, 'platform_dialogs'):
                    logger.error("[INSTAGRAM_HANDLER] Could not get platform dialog coordinator from UI context")
                    if self.error_handler:
                        self.error_handler.handle_service_failure("Instagram Handler", "authentication", "Could not access authentication dialog", url)
                    return
                
                platform_coordinator = ctx.platform_dialogs
                    
                def on_auth_complete(status):
                    """Callback after authentication completes.
                    
                    Args:
                        status: InstagramAuthStatus indicating authentication result
                    """
                    logger.info(f"[INSTAGRAM_HANDLER] Auth callback received status: {status}")
                    
                    if status == InstagramAuthStatus.AUTHENTICATED and self.instagram_auth_manager.is_authenticated():
                        logger.info("[INSTAGRAM_HANDLER] Authentication successful, download already added")
                        # Download was already added, nothing more to do
                    else:
                        logger.warning(f"[INSTAGRAM_HANDLER] Authentication failed or cancelled: {status}")
                        # Remove download if authentication failed
                        if download_index_ref["index"] is not None and hasattr(ctx, 'downloads'):
                            def remove_download():
                                try:
                                    ctx.downloads.remove_downloads([download_index_ref["index"]])
                                    logger.info(f"[INSTAGRAM_HANDLER] Removed download at index {download_index_ref['index']} due to auth failure")
                                except Exception as e:
                                    logger.error(f"[INSTAGRAM_HANDLER] Error removing download: {e}", exc_info=True)
                            schedule_on_main_thread(root, remove_download, immediate=True)
                        
                        # Show error in status bar
                        if self.message_queue:
                            error_msg = "Instagram authentication failed. Please try again."
                            self.message_queue.add_message(
                                Message(
                                    text=error_msg,
                                    level=MessageLevel.ERROR,
                                    title="Instagram Authentication Failed"
                                )
                            )

                # Trigger authentication (loading dialog will be shown after credentials are entered)
                platform_coordinator.authenticate_instagram(root, on_auth_complete)
                return

            # Already authenticated, proceed with download
            def process_instagram_download():
                try:
                    logger.info(f"[INSTAGRAM_HANDLER] Calling download callback for: {url}")
                    download_callback(url)
                    logger.info("[INSTAGRAM_HANDLER] Download callback executed")
                except Exception as e:
                    logger.error(f"[INSTAGRAM_HANDLER] Error processing Instagram download: {e}", exc_info=True)
                    if self.error_handler:
                        error_context = extract_error_context(e, "Instagram", "download processing", url)
                        self.error_handler.handle_exception(e, "Processing Instagram download", "Instagram")

            # Schedule on main thread
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
