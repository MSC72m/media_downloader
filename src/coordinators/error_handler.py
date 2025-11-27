"""Centralized error handler for consistent error display across all coordinators."""

from typing import Optional

from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorHandler, IMessageQueue
from src.services.events.queue import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandler(IErrorHandler):
    """Centralized error handling - single source of truth for error display.

    All errors are routed through message queue which displays them in status bar.
    This eliminates duplicate error handling code across coordinators.
    """

    def __init__(self, message_queue: Optional[IMessageQueue] = None):
        """Initialize with proper dependency injection.

        Args:
            message_queue: Message queue for displaying messages (optional)
        """
        self.message_queue = message_queue
        logger.info("[ERROR_HANDLER] Initialized with DI")

    def set_message_queue(self, message_queue: IMessageQueue) -> None:
        """Set message queue instance - used for late binding."""
        self.message_queue = message_queue
        logger.info("[ERROR_HANDLER] Message queue updated")

    def show_error(self, title: str, message: str) -> None:
        """Show error message via message queue.

        Args:
            title: Error title/category
            message: Error message text
        """
        if not self.message_queue:
            logger.error(f"[ERROR_HANDLER] Message queue not available. Error: {title} - {message}")
            return

        error_message = Message(text=message, level=MessageLevel.ERROR, title=title)
        self.message_queue.add_message(error_message)
        logger.debug(f"[ERROR_HANDLER] Error queued: {title}")

    def show_warning(self, title: str, message: str) -> None:
        """Show warning message via message queue.

        Args:
            title: Warning title/category
            message: Warning message text
        """
        if not self.message_queue:
            logger.warning(f"[ERROR_HANDLER] Message queue not available. Warning: {title} - {message}")
            return

        warning_message = Message(text=message, level=MessageLevel.WARNING, title=title)
        self.message_queue.add_message(warning_message)
        logger.debug(f"[ERROR_HANDLER] Warning queued: {title}")

    def show_info(self, title: str, message: str) -> None:
        """Show info message via message queue.

        Args:
            title: Info title/category
            message: Info message text
        """
        if not self.message_queue:
            logger.info(f"[ERROR_HANDLER] Message queue not available. Info: {title} - {message}")
            return

        info_message = Message(text=message, level=MessageLevel.INFO, title=title)
        self.message_queue.add_message(info_message)
        logger.debug(f"[ERROR_HANDLER] Info queued: {title}")

    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None:
        """Handle exception with automatic context extraction.

        Args:
            exception: The exception that occurred
            context: Additional context about where the error occurred
            service: Service name where error occurred (e.g., 'YouTube', 'Twitter')
        """
        error_msg = str(exception)
        error_type = type(exception).__name__

        title = f"{service} Error" if service else "Error"
        if context:
            message = f"{context}: {error_msg}"
        else:
            message = error_msg

        logger.error(f"[ERROR_HANDLER] Exception in {service or 'unknown'}: {error_type} - {message}", exc_info=True)
        self.show_error(title, message)

    def handle_service_failure(self, service: str, operation: str, error_message: str, url: str = "") -> None:
        """Handle service failure with service name and operation context.

        Args:
            service: Service name (e.g., 'YouTube', 'Twitter', 'Instagram')
            operation: Operation that failed (e.g., 'download', 'metadata fetch')
            error_message: Error message
            url: Optional URL where the failure occurred
        """
        title = f"{service} {operation.title()} Failed"
        if url:
            message = f"Failed to {operation} from {url}: {error_message}"
        else:
            message = f"Failed to {operation}: {error_message}"

        logger.error(f"[ERROR_HANDLER] {title}: {message}")
        self.show_error(title, message)
