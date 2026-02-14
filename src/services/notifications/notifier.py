from collections.abc import Mapping
from typing import TypedDict

from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IMessageQueue, INotifier
from src.services.events.queue import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


class _NotificationTemplate(TypedDict, total=False):
    text: str
    title: str
    level: str
    duration: int


class NotifierService(INotifier):
    def __init__(
        self,
        message_queue: IMessageQueue | None = None,
        custom_templates: Mapping[str, Mapping[str, object]] | None = None,
    ) -> None:
        self.message_queue = message_queue
        self._templates = self._get_templates()
        if custom_templates:
            for key, template in custom_templates.items():
                duration_raw = template.get("duration", 5000)
                duration = duration_raw if isinstance(duration_raw, int) else 5000
                self._templates[key] = {
                    "text": str(template.get("text", "")),
                    "title": str(template.get("title", "")),
                    "level": str(template.get("level", MessageLevel.INFO.name)),
                    "duration": duration,
                }

    def _get_templates(self) -> dict[str, _NotificationTemplate]:
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

    def notify_user(self, notification_type: str, **kwargs: object) -> None:
        if not (template_data := self._templates.get(notification_type)):
            logger.warning(f"[NOTIFIER] Template not found: {notification_type}")
            return

        message_data: _NotificationTemplate = template_data.copy()
        for key, value in kwargs.items():
            if key == "text":
                message_data["text"] = str(value)
            elif key == "title":
                message_data["title"] = str(value)
            elif key == "level":
                message_data["level"] = str(value)
            elif key == "duration" and isinstance(value, int):
                message_data["duration"] = value

        if not self.message_queue:
            return

        text = str(message_data.get("text", ""))
        level_name = str(message_data.get("level", MessageLevel.INFO.name))
        title_value = message_data.get("title")
        title = str(title_value) if isinstance(title_value, str) else None
        duration_value = message_data.get("duration", 5000)
        duration = duration_value if isinstance(duration_value, int) else 5000

        try:
            self.message_queue.add_message(
                Message(
                    text=text,
                    level=getattr(MessageLevel, level_name, MessageLevel.INFO),
                    title=title,
                    duration=duration,
                )
            )
        except Exception as e:
            logger.error(f"[NOTIFIER] Failed to send notification: {e}")

    def notify_error(self, error: Exception, context: str = "") -> None:
        self.notify_user(
            "download_error",
            text=f"Error in {context}: {error!s}",
        )
