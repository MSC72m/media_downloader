"""Base handler with common behaviors for all link handlers."""

from typing import Dict, Any, Optional
from enum import Enum

from src.core.interfaces import IMessageQueue
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class BaseHandler:
    """Base handler with common notification behavior for all handlers."""

    def __init__(self, message_queue: Optional[IMessageQueue] = None):
        self.message_queue = message_queue
        self._notification_templates = self._get_notification_templates()

    def _get_notification_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get notification templates. Override in subclasses for service-specific messages."""
        return {
            "cookies_generating": {
                "text": "Cookies are being generated. Please wait a moment and try again.",
                "title": "Cookies Generating",
                "level": "INFO",
            },
            "cookies_unavailable": {
                "text": "Cookies are not available. Some content may fail to download.",
                "title": "Cookies Unavailable",
                "level": "WARNING",
            },
            "authentication_required": {
                "text": "Authentication required. Please log in to continue.",
                "title": "Authentication Required",
                "level": "INFO",
            },
            "network_error": {
                "text": "Network connection error. Please check your internet connection.",
                "title": "Network Error",
                "level": "ERROR",
            },
            "service_unavailable": {
                "text": "Service is temporarily unavailable. Please try again later.",
                "title": "Service Unavailable",
                "level": "ERROR",
            },
            "download_error": {
                "text": "Failed to download content. Please check the URL and try again.",
                "title": "Download Error",
                "level": "ERROR",
            }
        }

    def notify_user(self, notification_type: str, **kwargs) -> None:
        """Notify user using template with polymorphic behavior."""
        template_data = self._notification_templates.get(notification_type)
        if not template_data:
            logger.warning(f"[HANDLER] Notification template not found: {notification_type}")
            return

        # Allow template customization through kwargs
        message_data = template_data.copy()
        message_data.update(kwargs)

        self._send_notification(message_data)

    def _send_notification(self, message_data: Dict[str, Any]) -> None:
        """Send notification using message queue."""
        if not self.message_queue:
            logger.debug(f"[HANDLER] No message queue available for notification: {message_data.get('title')}")
            return

        try:
            from src.core.enums.message_level import MessageLevel
            from src.services.events.queue import Message

            self.message_queue.add_message(
                Message(
                    text=message_data["text"],
                    level=getattr(MessageLevel, message_data["level"]),
                    title=message_data["title"],
                    duration=message_data.get("duration", 5000),
                )
            )
        except Exception as e:
            logger.error(f"[HANDLER] Failed to send notification: {e}")

    def notify_error(self, error: Exception, context: str = "") -> None:
        """Notify about errors with context."""
        self.notify_user(
            "download_error",
            text=f"Error in {context}: {str(error)}",
        )