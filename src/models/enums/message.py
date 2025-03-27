"""Enums for message levels."""
from enum import StrEnum


class MessageLevel(StrEnum):
    """Message levels for status updates."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error" 