"""Network status enum."""

from enum import StrEnum


class NetworkStatus(StrEnum):
    """Network connectivity statuses."""
    UNKNOWN = "unknown"
    CHECKING = "checking"
    CONNECTED = "connected"
    ERROR = "error"