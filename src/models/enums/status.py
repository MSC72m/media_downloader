"""Enums for download status."""
from enum import StrEnum


class DownloadStatus(StrEnum):
    """Status of a download item."""
    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    COMPLETED = "Completed"
    FAILED = "Failed"
    PAUSED = "Paused"
    CANCELLED = "Cancelled" 

class InstagramAuthStatus(StrEnum):
    """Status of Instagram authentication."""
    LOGGING_IN = "Logging in"
    AUTHENTICATED = "Authenticated"
    FAILED = "Failed"

class NetworkStatus(StrEnum):
    """Network connection status."""
    CHECKING = "Checking"
    CONNECTED = "Connected"
    ERROR = "Error"
    UNKNOWN = "Unknown"
