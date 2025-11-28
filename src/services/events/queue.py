"""Message queue for displaying UI messages via status bar."""

from collections.abc import Callable

from pydantic import BaseModel, Field

from src.core.enums import MessageLevel
from src.core.interfaces import IMessageQueue
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Message(BaseModel):
    """Message to display in the UI."""

    text: str
    level: MessageLevel = Field(default=MessageLevel.INFO)
    title: str | None = Field(default=None)
    duration: int = Field(default=5000, description="How long to display the message (ms)")

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True


class MessageQueue(IMessageQueue):
    """Queue for managing UI messages - routes all messages to status bar."""

    def __init__(self, status_bar):
        """Initialize with status bar reference.

        Args:
            status_bar: StatusBar component to display messages
        """
        self.status_bar = status_bar

    def add_message(self, message: Message):
        """Add a message to the queue (immediate forwarding to status bar).

        Args:
            message: Message to display
        """
        self._show_message(message)

    # IMessageQueue interface implementation
    def send_message(self, message: dict) -> None:
        """Send a message - implements IMessageQueue interface.

        Args:
            message: Dictionary with 'text', 'level', 'title' keys
        """
        # Convert dict to Message object
        msg = Message(
            text=message.get("text", ""),
            level=message.get("level", MessageLevel.INFO),
            title=message.get("title"),
            duration=message.get("duration", 5000),
        )
        self.add_message(msg)

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register message handler - implements IMessageQueue interface.

        Note: Current implementation routes all messages to status bar.
        This method is kept for interface compatibility.

        Args:
            message_type: Type of message (not used in current implementation)
            handler: Handler function (not used in current implementation)
        """
        # Current implementation routes all messages to status bar
        # Handler registration is not needed, but kept for interface compliance
        logger.debug(
            f"[MESSAGE_QUEUE] Handler registration requested for {message_type} (not used)"
        )

    def _show_message(self, message: Message):
        """Show the message in status bar based on level.

        Args:
            message: Message to display
        """
        if not self.status_bar:
            logger.error("[MESSAGE_QUEUE] Status bar not available!")
            return

        # Format message with title if provided
        text = f"{message.title}: {message.text}" if message.title else message.text

        # Route to appropriate status bar method based on level
        # StatusBar methods are thread-safe (they use their own queue)
        if message.level == MessageLevel.ERROR:
            self.status_bar.show_error(text)
        elif message.level == MessageLevel.WARNING:
            self.status_bar.show_warning(text)
        else:  # INFO, SUCCESS
            self.status_bar.show_message(text)
