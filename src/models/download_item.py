from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class DownloadItem:
    """Model representing a download item."""
    name: str
    url: str
    status: str = "Pending"
    progress: float = 0.0
    speed: float = 0.0
    created_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def update_progress(self, progress: float, speed: float):
        """Update download progress and speed."""
        self.progress = progress
        self.speed = speed
        if progress >= 100:
            self.status = "Completed"
            self.completed_at = datetime.now()

    def mark_failed(self, error_message: str):
        """Mark download as failed with error message."""
        self.status = "Failed"
        self.error_message = error_message
        self.completed_at = datetime.now()