"""Message queue for displaying UI messages via status bar."""

import queue
from typing import Optional

from pydantic import BaseModel, Field

from src.core.enums import MessageLevel
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Message(BaseModel):
    """Message to display in the UI."""

    text: str
    level: MessageLevel = Field(default=MessageLevel.INFO)
    title: Optional[str] = Field(default=None)
    duration: int = Field(
        default=5000, description="How long to display the message (ms)"
    )

    class Config:
        """Pydantic model configuration."""

        validate_assignment = True


class MessageQueue:
    """Queue for managing UI messages - routes all messages to status bar."""

    def __init__(self, status_bar):
        """Initialize with status bar reference.

        Args:
            status_bar: StatusBar component to display messages
        """
        self.queue: queue.Queue = queue.Queue()
        self.status_bar = status_bar
        self.processing = False
        self._start_processing()

    def _start_processing(self):
        """Start processing messages in the queue."""
        if self.processing:
            return

        def process_messages():
            try:
                while True:
                    try:
                        msg = self.queue.get_nowait()
                        self._show_message(msg)
                        self.queue.task_done()
                    except queue.Empty:
                        break
            except Exception as e:
                logger.error(
                    f"[MESSAGE_QUEUE] Error processing messages: {e}", exc_info=True
                )
            finally:
                self.processing = False

            # Schedule next check if there are messages
            if not self.queue.empty():
                self.processing = True
                # Use status_bar's root for scheduling
                if self.status_bar and hasattr(self.status_bar, "_root_window"):
                    self.status_bar._root_window.after(100, process_messages)

        self.processing = True
        # Initial schedule
        if self.status_bar and hasattr(self.status_bar, "_root_window"):
            self.status_bar._root_window.after(100, process_messages)

    def add_message(self, message: Message):
        """Add a message to the queue.

        Args:
            message: Message to display
        """
        self.queue.put(message)
        if not self.processing:
            self._start_processing()

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
        if message.level == MessageLevel.ERROR:
            self.status_bar.show_error(text)
        elif message.level == MessageLevel.WARNING:
            self.status_bar.show_warning(text)
        else:  # INFO, SUCCESS
            self.status_bar.show_message(text)
