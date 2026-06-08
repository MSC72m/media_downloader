from collections.abc import Callable, Mapping
from typing import Protocol

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
    def __init__(self, status_bar: "_StatusBarProtocol | None") -> None:
        self.status_bar = status_bar

    def add_message(self, message: Message | str | Mapping[str, object]) -> None:
        if isinstance(message, Message):
            self._show_message(message)
            return
        if isinstance(message, dict):
            self.send_message(message)
            return
        if isinstance(message, str):
            self._show_message(Message(text=message))
            return
        logger.warning("[MESSAGE_QUEUE] Unsupported message payload: %s", type(message).__name__)

    def send_message(self, message: Mapping[str, object]) -> None:
        raw_level = message.get("level")
        level = raw_level if isinstance(raw_level, MessageLevel) else MessageLevel.INFO
        raw_duration = message.get("duration")
        duration = (
            int(raw_duration)
            if isinstance(raw_duration, int | float | str) and str(raw_duration).isdigit()
            else 5000
        )
        msg = Message(
            text=str(message.get("text", "")),
            level=level,
            title=str(title) if (title := message.get("title")) is not None else None,
            duration=duration,
        )
        self.add_message(msg)

    def register_handler(self, message_type: str, handler: Callable[..., None]) -> None:
        logger.debug(
            f"[MESSAGE_QUEUE] Handler registration requested for {message_type} (not used)"
        )

    def _show_message(self, message: Message) -> None:
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


class _StatusBarProtocol(Protocol):
    def show_message(self, message: str) -> None: ...
    def show_warning(self, message: str) -> None: ...
    def show_error(self, message: str) -> None: ...
