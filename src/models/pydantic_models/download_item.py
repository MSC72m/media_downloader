"""Pydantic model for download items."""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from src.models.enums.status import DownloadStatus


class DownloadItem(BaseModel):
    """Model representing a download item."""
    name: str = Field(..., description="Name of the download item")
    url: str = Field(..., description="URL of the media to download")
    status: DownloadStatus = Field(default=DownloadStatus.PENDING, description="Current status of download")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Download progress percentage")
    speed: float = Field(default=0.0, ge=0.0, description="Download speed in bytes/second")
    created_at: datetime = Field(default_factory=datetime.now, description="When the item was created")
    completed_at: Optional[datetime] = Field(default=None, description="When the download completed or failed")
    error_message: Optional[str] = Field(default=None, description="Error message if download failed")
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
        arbitrary_types_allowed = True

    def update_progress(self, progress: float, speed: float):
        """Update download progress and speed."""
        self.progress = progress
        self.speed = speed
        if progress >= 100:
            self.status = DownloadStatus.COMPLETED
            self.completed_at = datetime.now()

    def mark_failed(self, error_message: str):
        """Mark download as failed with error message."""
        self.status = DownloadStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now() 