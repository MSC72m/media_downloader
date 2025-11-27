"""Base user notifier with polymorphic behavior."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

from src.core.enums.message_level import MessageLevel
from src.interfaces.service_interfaces import IMessageQueue
from src.services.events.queue import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class NotificationTemplate(Enum):
    """Predefined notification templates."""
    COOKIES_GENERATING = "cookies_generating"
    COOKIES_UNAVAILABLE = "cookies_unavailable"
    AUTHENTICATION_REQUIRED = "authentication_required"
    NETWORK_ERROR = "network_error"
    DOWNLOAD_ERROR = "download_error"
    DOWNLOAD_SUCCESS = "download_success"
    SERVICE_UNAVAILABLE = "service_unavailable"


class BaseUserNotifier(ABC):
    """Base class for user notification with polymorphic behavior."""

    def __init__(self, message_queue: IMessageQueue):
        self.message_queue = message_queue
        self._notification_templates = self._initialize_templates()

    @abstractmethod
    def _initialize_templates(self) -> Dict[NotificationTemplate, Dict[str, Any]]:
        """Initialize notification templates for specific service."""
        pass

    def notify_user(self, template: NotificationTemplate, **kwargs) -> None:
        """Notify user using template with polymorphic behavior."""
        template_data = self._notification_templates.get(template)
        if not template_data:
            logger.warning(f"[NOTIFIER] Template not found: {template}")
            return

        # Allow template customization through kwargs
        message_data = template_data.copy()
        message_data.update(kwargs)

        self._send_notification(message_data)

    def _send_notification(self, message_data: Dict[str, Any]) -> None:
        """Send notification - can be overridden for different notification methods."""
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
        """Notify about errors with context."""
        self.notify_user(
            NotificationTemplate.DOWNLOAD_ERROR,
            text=f"Error in {context}: {str(error)}",
            context=context
        )


class YouTubeNotifier(BaseUserNotifier):
    """YouTube-specific notifier."""

    def _initialize_templates(self) -> Dict[NotificationTemplate, Dict[str, Any]]:
        """Initialize YouTube-specific notification templates."""
        return {
            NotificationTemplate.COOKIES_GENERATING: {
                "text": "YouTube cookies are being generated. Please wait a moment and try again.",
                "title": "Cookies Generating",
                "level": NotificationType.INFO.value,
            },
            NotificationTemplate.COOKIES_UNAVAILABLE: {
                "text": "YouTube cookies are not available. Some videos may fail to download.",
                "title": "Cookies Unavailable",
                "level": NotificationType.WARNING.value,
            },
            NotificationTemplate.SERVICE_UNAVAILABLE: {
                "text": "YouTube service is temporarily unavailable. Please try again later.",
                "title": "YouTube Service Unavailable",
                "level": NotificationType.ERROR.value,
            },
            NotificationTemplate.DOWNLOAD_ERROR: {
                "text": "Failed to download YouTube video. Please check the URL and try again.",
                "title": "Download Error",
                "level": NotificationType.ERROR.value,
            }
        }


class InstagramNotifier(BaseUserNotifier):
    """Instagram-specific notifier."""

    def _initialize_templates(self) -> Dict[NotificationTemplate, Dict[str, Any]]:
        """Initialize Instagram-specific notification templates."""
        return {
            NotificationTemplate.AUTHENTICATION_REQUIRED: {
                "text": "Instagram authentication required. Please log in to continue.",
                "title": "Authentication Required",
                "level": NotificationType.INFO.value,
            },
            NotificationTemplate.SERVICE_UNAVAILABLE: {
                "text": "Instagram service is temporarily unavailable. Please try again later.",
                "title": "Instagram Service Unavailable",
                "level": NotificationType.ERROR.value,
            }
        }


class GenericNotifier(BaseUserNotifier):
    """Generic notifier for other services."""

    def _initialize_templates(self) -> Dict[NotificationTemplate, Dict[str, Any]]:
        """Initialize generic notification templates."""
        return {
            NotificationTemplate.NETWORK_ERROR: {
                "text": "Network connection error. Please check your internet connection.",
                "title": "Network Error",
                "level": NotificationType.ERROR.value,
            },
            NotificationTemplate.SERVICE_UNAVAILABLE: {
                "text": "Service is temporarily unavailable. Please try again later.",
                "title": "Service Unavailable",
                "level": NotificationType.ERROR.value,
            }
        }