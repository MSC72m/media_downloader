from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, field_validator, ValidationError, Field

"""
        self.youtube_options = {
            'quality': '720p',
            'playlist': False,
            'audio_only': False
        }
"""

class SubtitleOptions(BaseModel):
    download_sub: bool = Field(False, description="Set to True in order to download subtitles (more config required), Default False")
    embed: bool = Field(True, description="Set to True|False to embed subtitles to video directly, Default True")
    sep_file: bool = Field(False, description="Set to True|False to download subtitles in separate file, Default False")
    lang: str = Field("eng", description="Subtitle Language. Select in provided List.")

    @field_validator('embed', 'sep_file', mode='before')
    def validate(cls, value, values):
        if values.get('download_sub') is False and value:
            raise ValueError("Cannot enable 'embed' or 'sep_file' if 'download_sub' is False.")
        return value  # Return the validated value, not `values`

class YtOptions(BaseModel):
    quality: str = Field("720p", description="YT video quality, 480p,720p,1080p. Default set to 720p")
    playlist: bool = Field(False, description="Download whole playlist of provided url. Default False")
    audio_only: bool = Field(False, description="Download Audio file of provided url. Default False")
    subtitle_setting: SubtitleOptions = Field(default_factory=SubtitleOptions, description="Download subtitles of provided url. Default False")


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