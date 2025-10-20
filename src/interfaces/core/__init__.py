"""Core interfaces for the media downloader application."""

from .event_handlers import (
    URLDetectionHandler,
    DownloadManagementHandler,
    UIUpdateHandler,
    AuthenticationHandler,
    FileManagementHandler,
    ConfigurationHandler,
    NetworkStatusHandler,
    YouTubeSpecificHandler
)

__all__ = [
    'URLDetectionHandler',
    'DownloadManagementHandler',
    'UIUpdateHandler',
    'AuthenticationHandler',
    'FileManagementHandler',
    'ConfigurationHandler',
    'NetworkStatusHandler',
    'YouTubeSpecificHandler'
]
