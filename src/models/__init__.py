"""Core models for the media downloader application."""
from .core import (
    DownloadItem,
    UIMessage,
    InstagramAuthState,
    InstagramCredentials,
    DownloadOptions,
    UIState,
    # Backward compatibility
    AuthState,
    Credentials
)
from .enums import (
    DownloadStatus,
    InstagramAuthStatus,
    NetworkStatus,
    UITheme,
    MessageLevel,
    VideoQuality,
    ServiceType,
    ButtonState
)

__all__ = [
    "DownloadItem",
    "UIMessage",
    "InstagramAuthState",
    "InstagramCredentials",
    "DownloadOptions",
    "UIState",
    "AuthState",
    "Credentials",
    "DownloadStatus",
    "InstagramAuthStatus",
    "NetworkStatus",
    "UITheme",
    "MessageLevel",
    "VideoQuality",
    "ServiceType",
    "ButtonState"
]
