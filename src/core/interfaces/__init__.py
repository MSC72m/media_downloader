"""Interface definitions following Interface Segregation Principle."""

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