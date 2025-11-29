from collections.abc import Callable

from pydantic import BaseModel, Field

from src.core.enums import MessageLevel
from src.core.interfaces import IMessageQueue
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Message(BaseModel):
    text: str
    level: MessageLevel = Field(default=MessageLevel.INFO)
    title: str | None = Field(default=None)
    duration: int = Field(default=5000, description="How long to display the message (ms)")

    class Config:
        validate_assignment = True


class MessageQueue(IMessageQueue):
    def __init__(self, status_bar):
        self.status_bar = status_bar

    def add_message(self, message: Message):
        self._show_message(message)

    def send_message(self, message: dict) -> None:
        msg = Message(
            text=message.get("text", ""),
            level=message.get("level", MessageLevel.INFO),
            title=message.get("title"),
            duration=message.get("duration", 5000),
        )
        self.add_message(msg)

    def register_handler(self, message_type: str, handler: Callable) -> None:
        logger.debug(
            f"[MESSAGE_QUEUE] Handler registration requested for {message_type} (not used)"
        )

    def _show_message(self, message: Message):
        if not self.status_bar:
            logger.error("[MESSAGE_QUEUE] Status bar not available!")
            return

        text = f"{message.title}: {message.text}" if message.title else message.text

        if message.level == MessageLevel.ERROR:
            self.status_bar.show_error(text)
        elif message.level == MessageLevel.WARNING:
            self.status_bar.show_warning(text)
        else:
            self.status_bar.show_message(text)
