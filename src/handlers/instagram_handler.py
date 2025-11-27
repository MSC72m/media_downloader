"""Instagram link handler implementation."""

import re
from typing import Any, Callable, Dict, Optional

from src.core.config import get_config, AppConfig
from src.core.base.base_handler import BaseHandler
from src.interfaces.service_interfaces import IErrorHandler
from src.services.instagram.auth_manager import InstagramAuthManager
from src.services.detection.link_detector import (
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)
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
        from src.core.config import get_config
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

            # Check if authenticated, if not trigger authentication flow
            if not self.instagram_auth_manager.is_authenticated():
                logger.info("[INSTAGRAM_HANDLER] Instagram not authenticated, triggering auth flow")
                
                # Get platform dialog coordinator from UI context (polymorphic access)
                ctx = get_ui_context(ui_context)
                if not ctx or not hasattr(ctx, 'platform_dialogs'):
                    logger.error("[INSTAGRAM_HANDLER] Could not get platform dialog coordinator from UI context")
                    if self.error_handler:
                        self.error_handler.handle_service_failure("Instagram Handler", "authentication", "Could not access authentication dialog", url)
                    return
                
                platform_coordinator = ctx.platform_dialogs
                    
                def on_auth_complete():
                    """Callback after authentication completes."""
                    if self.instagram_auth_manager.is_authenticated():
                        logger.info("[INSTAGRAM_HANDLER] Authentication successful, proceeding with download")
                        # Proceed with download after successful authentication
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
                        
                        schedule_on_main_thread(root, process_instagram_download, immediate=True)
                    else:
                        logger.warning("[INSTAGRAM_HANDLER] Authentication failed or cancelled")

                # Trigger authentication
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
