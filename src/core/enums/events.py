from enum import Enum, auto


class DownloadEvent(Enum):
    """Download event types."""

    PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    STARTED = auto()
