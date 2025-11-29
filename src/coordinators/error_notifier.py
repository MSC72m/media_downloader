from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.events.queue import Message
from src.utils.error_helpers import (
    extract_error_context,
    format_user_friendly_error,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorNotifier(IErrorNotifier):
    """Centralized error handling - single source of truth for error display.

    All errors are routed through message queue which displays them in status bar.
    This eliminates duplicate error handling code across coordinators.
    """

    def __init__(self, message_queue: IMessageQueue | None = None):
        """Initialize with proper dependency injection.

        Args:
            message_queue: Message queue for displaying messages (optional)
        """
        self.message_queue = message_queue
        logger.info("[ERROR_NOTIFIER] Initialized with DI")

    def set_message_queue(self, message_queue: IMessageQueue) -> None:
        """Set message queue instance - used for late binding."""
        self.message_queue = message_queue
        logger.info("[ERROR_NOTIFIER] Message queue updated")

    def show_error(self, title: str, message: str) -> None:
        """Show error message via message queue.

        Args:
            title: Error title/category
            message: Error message text
        """
        if not self.message_queue:
            logger.error(
                f"[ERROR_NOTIFIER] Message queue not available. Error: {title} - {message}"
            )
            return

        error_message = Message(text=message, level=MessageLevel.ERROR, title=title)
        self.message_queue.add_message(error_message)
        logger.debug(f"[ERROR_NOTIFIER] Error queued: {title}")

    def show_warning(self, title: str, message: str) -> None:
        """Show warning message via message queue.

        Args:
            title: Warning title/category
            message: Warning message text
        """
        if not self.message_queue:
            logger.warning(
                f"[ERROR_NOTIFIER] Message queue not available. Warning: {title} - {message}"
            )
            return

        warning_message = Message(text=message, level=MessageLevel.WARNING, title=title)
        self.message_queue.add_message(warning_message)
        logger.debug(f"[ERROR_NOTIFIER] Warning queued: {title}")

    def show_info(self, title: str, message: str) -> None:
        """Show info message via message queue.

        Args:
            title: Info title/category
            message: Info message text
        """
        if not self.message_queue:
            logger.info(f"[ERROR_NOTIFIER] Message queue not available. Info: {title} - {message}")
            return

        info_message = Message(text=message, level=MessageLevel.INFO, title=title)
        self.message_queue.add_message(info_message)
        logger.debug(f"[ERROR_NOTIFIER] Info queued: {title}")

    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None:
        """Handle exception with automatic context extraction using utility functions.

        Args:
            exception: The exception that occurred
            context: Additional context about where the error occurred
            service: Service name where error occurred (e.g., 'YouTube', 'Twitter')
        """
        error_context = extract_error_context(exception, service=service, operation=context)

        message = format_user_friendly_error(error_context)

        title = f"{service} Error" if service else "Error"

        logger.error(
            f"[ERROR_NOTIFIER] Exception in {service or 'unknown'}: {error_context.get('error_type')} - {message}",
            exc_info=True,
        )
        self.show_error(title, message)

    def handle_service_failure(
        self, service: str, operation: str, error_message: str, url: str = ""
    ) -> None:
        """Handle service failure with consistent error formatting.

        Args:
            service: Service name where error occurred
            operation: Operation that failed
            error_message: Error message
            url: URL where error occurred (optional)
        """
        error_context = {
            "error_type": "ServiceError",
            "error_message": error_message,
            "service": service,
            "operation": operation,
            "url": url,
        }

        message = format_user_friendly_error(error_context)

        title = (
            f"{service} {operation.title()} Failed" if service and operation else "Service Error"
        )

        logger.error(
            f"[ERROR_NOTIFIER] Service failure: {service or 'unknown'} - {operation or 'unknown'}: {message}"
        )
        self.show_error(title, message)
