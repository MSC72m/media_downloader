"""Core models using Pydantic with fallback support."""

from typing import Optional, List, Dict
from datetime import datetime
from enum import StrEnum

try:
    from pydantic import BaseModel, Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback implementation without pydantic
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def dict(self):
            return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    def Field(*args, **kwargs):
        return None

    def validator(func):
        return func

    PYDANTIC_AVAILABLE = False

from .enums.download_status import DownloadStatus
from .enums.service_type import ServiceType


class Download(BaseModel):
    """Model representing a download item with individual configuration."""

    if PYDANTIC_AVAILABLE:
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
        # Set defaults using BaseModel or manually
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            self.name = kwargs.get('name', '')
            self.url = kwargs.get('url', '')
            self.status = kwargs.get('status', DownloadStatus.PENDING)
            self.progress = kwargs.get('progress', 0.0)
            self.speed = kwargs.get('speed', 0.0)
            self.created_at = kwargs.get('created_at', datetime.now())
            self.completed_at = kwargs.get('completed_at')
            self.error_message = kwargs.get('error_message')
            self.service_type = kwargs.get('service_type')

            # Individual download options
            self.quality = kwargs.get('quality', '720p')
            self.format = kwargs.get('format', 'video')
            self.audio_only = kwargs.get('audio_only', False)
            self.video_only = kwargs.get('video_only', False)
            self.download_playlist = kwargs.get('download_playlist', False)
            self.download_subtitles = kwargs.get('download_subtitles', False)
            self.selected_subtitles = kwargs.get('selected_subtitles')
            self.download_thumbnail = kwargs.get('download_thumbnail', True)
            self.embed_metadata = kwargs.get('embed_metadata', True)
            self.cookie_path = kwargs.get('cookie_path')
            self.selected_browser = kwargs.get('selected_browser')
            self.speed_limit = kwargs.get('speed_limit')
            self.retries = kwargs.get('retries', 3)
            self.concurrent_downloads = kwargs.get('concurrent_downloads', 1)

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

    def __init__(self, **kwargs):
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            self.save_directory = kwargs.get('save_directory', "~/Downloads")


class UIState(BaseModel):
    """Main UI state model."""

    if PYDANTIC_AVAILABLE:
        download_directory: str = Field(default="~/Downloads")
        show_options_panel: bool = Field(default=False)
        selected_indices: list = Field(default_factory=list)

    def __init__(self, **kwargs):
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            self.download_directory = kwargs.get('download_directory', "~/Downloads")
            self.show_options_panel = kwargs.get('show_options_panel', False)
            self.selected_indices = kwargs.get('selected_indices', [])


class AuthState(BaseModel):
    """Authentication state for services."""

    def __init__(self, **kwargs):
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            self.is_authenticated = kwargs.get('is_authenticated', False)
            self.service = kwargs.get('service')
            self.username = kwargs.get('username')


class ButtonState(StrEnum):
    """Button state enumeration."""
    REMOVE = "remove"
    CLEAR = "clear"
    DOWNLOAD = "download"
    SETTINGS = "settings"
    CANCEL = "cancel"


class ConnectionResult(BaseModel):
    """Result of a connection check."""

    def __init__(self, **kwargs):
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            self.is_connected = kwargs.get('is_connected', False)
            self.error_message = kwargs.get('error_message', '')
            self.response_time = kwargs.get('response_time', 0.0)
            self.service_type = kwargs.get('service_type')


class DownloadResult(BaseModel):
    """Result of a download operation."""

    def __init__(self, **kwargs):
        if PYDANTIC_AVAILABLE:
            super().__init__(**kwargs)
        else:
            self.success = kwargs.get('success', False)
            self.file_path = kwargs.get('file_path')
            self.bytes_downloaded = kwargs.get('bytes_downloaded', 0)
            self.error_message = kwargs.get('error_message', '')
            self.download_time = kwargs.get('download_time', 0.0)