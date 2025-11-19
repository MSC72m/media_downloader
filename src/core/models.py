"""Core models - requires pydantic (no fallbacks)."""

from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums.download_status import DownloadStatus
from .enums.service_type import ServiceType

if TYPE_CHECKING:
    from src.services.events.event_bus import DownloadEventBus


class CookieState(BaseModel):
    """State model for cookie generation and management."""

    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now() + timedelta(hours=8)
    )
    is_valid: bool = Field(default=False)
    is_generating: bool = Field(default=False)
    cookie_path: Optional[str] = None
    error_message: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if cookies are expired."""
        return datetime.now() >= self.expires_at

    def should_regenerate(self) -> bool:
        """Check if cookies should be regenerated."""
        return (
            not self.is_valid
            or self.is_expired()
            or not self.cookie_path
            or not Path(self.cookie_path).exists()
        )


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
    speed_limit: Optional[int] = None
    retries: int = Field(default=3)
    concurrent_downloads: int = Field(default=1)

    # Event bus for state changes
    _event_bus: Optional["DownloadEventBus"] = None

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, "url") and self.url:
            self._validate_url(self.url)

    def set_event_bus(self, event_bus: "DownloadEventBus") -> None:
        """Set the event bus for this download."""
        self._event_bus = event_bus

    def _validate_url(self, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

    def update_progress(self, progress: float, speed: float):
        """Update download progress and speed."""
        from src.utils.logger import get_logger

        logger = get_logger(__name__)

        self.progress = progress
        self.speed = speed

        if not self._event_bus:
            logger.warning(f"[DOWNLOAD] {self.name} - NO EVENT BUS ATTACHED")
            return

        logger.info(f"[DOWNLOAD] {self.name} - Publishing progress: {progress}%")

        from src.services.events.event_bus import DownloadEvent

        self._event_bus.publish(
            DownloadEvent.PROGRESS, download=self, progress=progress, speed=speed
        )

        if progress >= 100:
            logger.info(f"[DOWNLOAD] {self.name} - Publishing completion")
            self.status = DownloadStatus.COMPLETED
            self.completed_at = datetime.now()
            self._event_bus.publish(DownloadEvent.COMPLETED, download=self)

    def mark_failed(self, error_message: str):
        """Mark download as failed with error message."""
        self.status = DownloadStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()

        if self._event_bus:
            from src.services.events.event_bus import DownloadEvent

            self._event_bus.publish(
                DownloadEvent.FAILED, download=self, error=error_message
            )


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
