"""Core models using Pydantic."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field, validator
from .enums.download_status import DownloadStatus
from .enums.service_type import ServiceType


class Download(BaseModel):
    """Model representing a download item."""
    name: str = Field(..., description="Name of the download item")
    url: str = Field(..., description="URL of the media to download")
    status: DownloadStatus = Field(default=DownloadStatus.PENDING, description="Current status of download")
    progress: float = Field(default=0.0, ge=0.0, le=100.0, description="Download progress percentage")
    speed: float = Field(default=0.0, ge=0.0, description="Download speed in bytes/second")
    created_at: datetime = Field(default_factory=datetime.now, description="When the item was created")
    completed_at: Optional[datetime] = Field(default=None, description="When the download completed or failed")
    error_message: Optional[str] = Field(default=None, description="Error message if download failed")
    service_type: Optional[ServiceType] = Field(default=None, description="Service type for this download")

    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v

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

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
        arbitrary_types_allowed = True


class DownloadOptions(BaseModel):
    """Options for downloading media."""
    quality: str = Field(default="720p", description="Video quality to download")
    playlist: bool = Field(default=False, description="Download entire playlist")
    audio_only: bool = Field(default=False, description="Download audio only")
    save_directory: str = Field(default="~/Downloads", description="Directory to save downloaded files")

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class UIState(BaseModel):
    """Main UI state model."""
    download_directory: str = Field(default="~/Downloads")
    show_options_panel: bool = Field(default=False)
    selected_indices: List[int] = Field(default_factory=list)

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class AuthState(BaseModel):
    """Authentication state for services."""
    is_authenticated: bool = Field(default=False)
    service: Optional[ServiceType] = Field(default=None)
    username: Optional[str] = Field(default=None)

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class InstagramAuthState(AuthState):
    """Instagram-specific authentication state."""
    session_data: Optional[Dict[str, Any]] = Field(default=None)


class InstagramCredentials(BaseModel):
    """Instagram login credentials."""
    username: str
    password: str
    remember: bool = Field(default=False)

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
        # This allows using SecretStr for passwords in the future
        arbitrary_types_allowed = True


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

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class DownloadResult(BaseModel):
    """Result of a download operation."""
    success: bool
    file_path: Optional[str] = None
    bytes_downloaded: int = 0
    error_message: str = ""
    download_time: float = 0.0

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True