from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .config import get_config
from .enums.download_status import DownloadStatus
from .enums.events import DownloadEvent
from .enums.service_type import ServiceType

if TYPE_CHECKING:
    from .interfaces.event_bus import IEventBus


class CookieState(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(default_factory=lambda: datetime.now() + timedelta(hours=8))
    is_valid: bool = Field(default=False)
    is_generating: bool = Field(default=False)
    cookie_path: str | None = None
    error_message: str | None = None

    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at

    def should_regenerate(self) -> bool:
        if not self.is_valid or not self.cookie_path:
            return True

        if self.is_expired():
            return True

        config = get_config()
        if self.generated_at:
            age_hours = (datetime.now() - self.generated_at).total_seconds() / 3600
            if age_hours >= config.cookies.cookie_expiry_hours:
                return True

        return False


class Download(BaseModel):
    name: str
    url: str
    status: DownloadStatus = Field(default=DownloadStatus.PENDING)
    progress: float = Field(default=0.0)
    speed: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error_message: str | None = None
    service_type: ServiceType | None = None

    quality: str | None = Field(default_factory=lambda: get_config().youtube.default_quality)
    format: str | None = Field(default="video")
    audio_only: bool = Field(default=False)
    video_only: bool = Field(default=False)
    download_playlist: bool = Field(default=False)
    download_subtitles: bool = Field(default=False)
    selected_subtitles: list[dict[str, str]] | None = None
    download_thumbnail: bool = Field(default=True)
    embed_metadata: bool = Field(default=True)
    cookie_path: str | None = None
    speed_limit: int | None = None
    retries: int = Field(default=3)
    concurrent_downloads: int = Field(default=1)

    _event_bus: IEventBus | None = None

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, "url") and self.url:
            self._validate_url(self.url)

    def set_event_bus(self, event_bus: IEventBus) -> None:
        self._event_bus = event_bus

    def _validate_url(self, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

    def update_progress(self, progress: float, speed: float):
        self.progress = progress
        self.speed = speed

        if not self._event_bus:
            return

        self._event_bus.publish(
            DownloadEvent.PROGRESS, download=self, progress=progress, speed=speed
        )

        if progress >= 100 and self.status != DownloadStatus.COMPLETED:
            self.status = DownloadStatus.COMPLETED
            if not self.completed_at:
                self.completed_at = datetime.now()
            self._event_bus.publish(DownloadEvent.COMPLETED, download=self)

    def mark_failed(self, error_message: str):
        self.status = DownloadStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now()

        if self._event_bus:
            self._event_bus.publish(DownloadEvent.FAILED, download=self, error=error_message)


class DownloadOptions(BaseModel):
    save_directory: str = Field(default_factory=lambda: str(get_config().paths.downloads_dir))


class UIState(BaseModel):
    download_directory: str = Field(default_factory=lambda: str(get_config().paths.downloads_dir))
    show_options_panel: bool = Field(default=False)
    selected_indices: list = Field(default_factory=list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class AuthState(BaseModel):
    is_authenticated: bool = Field(default=False)
    service: ServiceType | None = None
    username: str | None = None


class ButtonState(StrEnum):
    REMOVE = "remove"
    CLEAR = "clear"
    DOWNLOAD = "download"
    SETTINGS = "settings"
    CANCEL = "cancel"


class ConnectionResult(BaseModel):
    is_connected: bool
    error_message: str = ""
    response_time: float = 0.0
    service_type: ServiceType | None = None


class DownloadResult(BaseModel):
    success: bool
    file_path: str | None = None
    bytes_downloaded: int = 0
    error_message: str = ""
    download_time: float = 0.0
