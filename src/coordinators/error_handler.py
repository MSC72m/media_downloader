"""Centralized error handler for consistent error display across all coordinators."""

from src.core.enums.message_level import MessageLevel
from src.services.events.queue import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandler:
    """Centralized error handling - single source of truth for error display.

    All errors are routed through message queue which displays them in status bar.
    This eliminates duplicate error handling code across coordinators.
    """

    def __init__(self, container):
        """Initialize with service container.

        Args:
            container: Service container to access message_queue
        """
        self.container = container
        logger.info("[ERROR_HANDLER] Initialized")

    def show_error(self, title: str, message: str) -> None:
        """Show error message via message queue.

        Args:
            title: Error title/category
            message: Error message text
        """
        message_queue = self.container.get("message_queue")
        if not message_queue:
            logger.error(
                f"[ERROR_HANDLER] Message queue not available - cannot show error: {title}: {message}"
            )
            return

        error_message = Message(text=message, level=MessageLevel.ERROR, title=title)
        message_queue.add_message(error_message)
        logger.debug(f"[ERROR_HANDLER] Error queued: {title}")

    def show_warning(self, title: str, message: str) -> None:
        """Show warning message via message queue.

        Args:
            title: Warning title/category
            message: Warning message text
        """
        message_queue = self.container.get("message_queue")
        if not message_queue:
            logger.warning(
                f"[ERROR_HANDLER] Message queue not available - cannot show warning: {title}: {message}"
            )
            return

        warning_message = Message(text=message, level=MessageLevel.WARNING, title=title)
        message_queue.add_message(warning_message)
        logger.debug(f"[ERROR_HANDLER] Warning queued: {title}")

    def show_info(self, title: str, message: str) -> None:
        """Show info message via message queue.

        Args:
            title: Info title/category
            message: Info message text
        """
        message_queue = self.container.get("message_queue")
        if not message_queue:
            logger.info(
                f"[ERROR_HANDLER] Message queue not available - cannot show info: {title}: {message}"
            )
            return

        info_message = Message(text=message, level=MessageLevel.INFO, title=title)
        message_queue.add_message(info_message)
        logger.debug(f"[ERROR_HANDLER] Info queued: {title}")
