"""Core enums for the media downloader application."""
from .core import (
    DownloadStatus,
    InstagramAuthStatus,
    NetworkStatus,
    UITheme,
    MessageLevel,
    VideoQuality,
    ServiceType,
    ButtonState,
    # Backward compatibility
    DownloadStatusEnum,
    NetworkStatusEnum,
    InstagramAuthStatusEnum
)

__all__ = [
    "DownloadStatus",
    "InstagramAuthStatus",
    "NetworkStatus",
    "UITheme",
    "MessageLevel",
    "VideoQuality",
    "ServiceType",
    "ButtonState",
    "DownloadStatusEnum",
    "NetworkStatusEnum",
    "InstagramAuthStatusEnum"
] 