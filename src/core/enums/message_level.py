"""Message level enum."""

from .compat import StrEnum


class MessageLevel(StrEnum):
    """Message severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
