"""File service models using Pydantic."""

from typing import Optional
from pydantic import BaseModel, Field


class DownloadResult(BaseModel):
    """Result of a download operation."""
    success: bool
    file_path: Optional[str] = Field(default=None, description="Path to downloaded file")
    bytes_downloaded: int = Field(default=0, ge=0, description="Number of bytes downloaded")
    error_message: str = Field(default="", description="Error message if download failed")
    download_time: float = Field(default=0.0, ge=0.0, description="Time taken for download in seconds")

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
