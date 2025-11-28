"""Notifier service implementation."""

from typing import Any

from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IMessageQueue, INotifier
from src.services.events.queue import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NotifierService(INotifier):
    def __init__(
        self,
        message_queue: IMessageQueue | None = None,
        custom_templates: dict[str, dict[str, Any]] | None = None,
    ):
        self.message_queue = message_queue
        self._templates = self._get_templates()
        if custom_templates:
            self._templates.update(custom_templates)

    def _get_templates(self) -> dict[str, dict[str, Any]]:
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
            },
        }

    def notify_user(self, notification_type: str, **kwargs: Any) -> None:
        template_data = self._templates.get(notification_type)
        if not template_data:
            logger.warning(f"[NOTIFIER] Template not found: {notification_type}")
            return

        message_data = template_data.copy()
        message_data.update(kwargs)

        if not self.message_queue:
            return

        try:
            self.message_queue.add_message(
                Message(
                    text=message_data["text"],
                    level=getattr(MessageLevel, message_data["level"]),
                    title=message_data["title"],
                    duration=message_data.get("duration", 5000),
                )
            )
        except Exception as e:
            logger.error(f"[NOTIFIER] Failed to send notification: {e}")

    def notify_error(self, error: Exception, context: str = "") -> None:
        self.notify_user(
            "download_error",
            text=f"Error in {context}: {error!s}",
        )
