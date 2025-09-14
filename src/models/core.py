"""Core Pydantic models for the media downloader application."""
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field, SecretStr, validator
from .enums.core import (
    DownloadStatus, UITheme, MessageLevel, VideoQuality,
    ButtonState
)


class UIMessage(BaseModel):
    """Message to display in the UI."""
    text: str
    level: MessageLevel = Field(default=MessageLevel.INFO)
    duration: int = Field(default=5000, description="How long to display the message (ms)")

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


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


class InstagramAuthState(BaseModel):
    """Authentication state for Instagram."""
    is_authenticated: bool = Field(default=False)
    username: Optional[str] = Field(default=None)

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class InstagramCredentials(BaseModel):
    """Credentials for Instagram authentication."""
    username: str
    password: SecretStr
    remember: bool = Field(default=False)

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class DownloadOptions(BaseModel):
    """Options for downloading media."""
    quality: VideoQuality = Field(default=VideoQuality.HD, description="Video quality to download")
    playlist: bool = Field(default=False, description="Download entire playlist")
    audio_only: bool = Field(default=False, description="Download audio only")
    save_directory: str = Field(default="~/Downloads", description="Directory to save downloaded files")

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
        arbitrary_types_allowed = True


class UIState(BaseModel):
    """Main UI state model."""
    theme: UITheme = Field(default=UITheme.DARK)
    download_directory: str = Field(default="~/Downloads")
    last_message: Optional[UIMessage] = Field(default=None)
    show_options_panel: bool = Field(default=False)
    selected_indices: List[int] = Field(default_factory=list)

    # Button states - now using ButtonState enum for type safety
    button_states: Dict[ButtonState, bool] = Field(
        default_factory=lambda: {
            ButtonState.ADD: True,
            ButtonState.REMOVE: False,
            ButtonState.CLEAR: False,
            ButtonState.DOWNLOAD: False,
            ButtonState.CANCEL: False,
            ButtonState.PAUSE: False,
            ButtonState.RESUME: False,
            ButtonState.SETTINGS: True,
            ButtonState.INSTAGRAM_LOGIN: True,
            ButtonState.INSTAGRAM_LOGOUT: False
        }
    )

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True

    def update_button_states(self, has_selection: bool, has_items: bool, is_downloading: bool = False):
        """Update button states based on app state."""
        self.button_states[ButtonState.REMOVE] = has_selection and not is_downloading
        self.button_states[ButtonState.CLEAR] = has_items and not is_downloading
        self.button_states[ButtonState.DOWNLOAD] = has_items and not is_downloading
        self.button_states[ButtonState.CANCEL] = is_downloading
        self.button_states[ButtonState.PAUSE] = is_downloading
        self.button_states[ButtonState.RESUME] = False  # Only enabled when specifically paused

    def get_button_state(self, button_name: str) -> bool:
        """Get button state by name (for backward compatibility)."""
        try:
            button_state = ButtonState(button_name)
            return self.button_states[button_state]
        except ValueError:
            return False

    def set_button_state(self, button_name: str, state: bool):
        """Set button state by name (for backward compatibility)."""
        try:
            button_state = ButtonState(button_name)
            self.button_states[button_state] = state
        except ValueError:
            pass


# For backward compatibility
AuthState = InstagramAuthState
Credentials = InstagramCredentials