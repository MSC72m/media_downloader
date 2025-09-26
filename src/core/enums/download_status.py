"""Download status enum."""

from enum import StrEnum


class DownloadStatus(StrEnum):
    """Status of a download item."""
    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    COMPLETED = "Completed"
    FAILED = "Failed"
    PAUSED = "Paused"
    CANCELLED = "Cancelled"