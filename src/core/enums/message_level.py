"""Message level enum."""

from enum import StrEnum


class MessageLevel(StrEnum):
    """Message severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"