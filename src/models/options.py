"""Pydantic models for download options."""
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


class VideoQuality(str, Enum):
    """Available video quality options."""
    HIGHEST = "highest"
    LOWEST = "lowest"
    UHD_4K = "2160p"
    QHD = "1440p"
    FHD = "1080p"
    HD = "720p"
    SD = "480p"
    LD = "360p"
    VERY_LOW = "240p"
    LOWEST_QUALITY = "144p"


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