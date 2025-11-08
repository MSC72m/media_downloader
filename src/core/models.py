"""Core models - requires pydantic (no fallbacks)."""

from typing import Optional, List, Dict
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field

from .enums.download_status import DownloadStatus
from .enums.service_type import ServiceType


class Download(BaseModel):
    """Model representing a download item with individual configuration."""

    name: str
    url: str
    status: DownloadStatus = Field(default=DownloadStatus.PENDING)
    progress: float = Field(default=0.0)
    speed: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    service_type: Optional[ServiceType] = None

    # Individual download options for YouTube items
    quality: Optional[str] = Field(default="720p")
    format: Optional[str] = Field(default="video")
    audio_only: bool = Field(default=False)
    video_only: bool = Field(default=False)
    download_playlist: bool = Field(default=False)
    download_subtitles: bool = Field(default=False)
    selected_subtitles: Optional[List[Dict[str, str]]] = None
    download_thumbnail: bool = Field(default=True)
    embed_metadata: bool = Field(default=True)
    cookie_path: Optional[str] = None
    selected_browser: Optional[str] = None
    speed_limit: Optional[int] = None
    retries: int = Field(default=3)
    concurrent_downloads: int = Field(default=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Validate URL
        if hasattr(self, 'url') and self.url:
            self._validate_url(self.url)

    def _validate_url(self, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

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


class DownloadOptions(BaseModel):
    """Options for downloading media."""

    save_directory: str = Field(default="~/Downloads")


class UIState(BaseModel):
    """Main UI state model."""

    download_directory: str = Field(default="~/Downloads")
    show_options_panel: bool = Field(default=False)
    selected_indices: list = Field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class AuthState(BaseModel):
    """Authentication state for services."""

    is_authenticated: bool = Field(default=False)
    service: Optional[ServiceType] = None
    username: Optional[str] = None


class ButtonState(StrEnum):
    """Button state enumeration."""
    REMOVE = "remove"
    CLEAR = "clear"
    DOWNLOAD = "download"
    SETTINGS = "settings"
    CANCEL = "cancel"


class ConnectionResult(BaseModel):
    """Result of a connection check."""

    is_connected: bool
    error_message: str = ""
    response_time: float = 0.0
    service_type: Optional[ServiceType] = None


class DownloadResult(BaseModel):
    """Result of a download operation."""

    success: bool
    file_path: Optional[str] = None
    bytes_downloaded: int = 0
    error_message: str = ""
    download_time: float = 0.0