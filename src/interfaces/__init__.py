"""Abstraction layer interfaces for the media downloader application."""

from .cookie_detection import BrowserType, ICookieDetector, ICookieManager, PlatformType
from .protocols import (
    HasCleanupProtocol,
    HasClearProtocol,
    HasCompletedDownloadsProtocol,
    HasEventCoordinatorProtocol,
    TkRootProtocol,
    UIContextProtocol,
)
from .service_interfaces import (
    BaseDownloader,
    IAutoCookieManager,
    ICookieHandler,
    IDownloadHandler,
    IDownloadService,
    IErrorHandler,
    IFileService,
    IMessageQueue,
    IMetadataService,
    INetworkChecker,
    IServiceFactory,
    IUIState,
    AuthenticationError,
    NetworkError,
    ServiceError,
)
from .youtube_metadata import IYouTubeMetadataService, SubtitleInfo, YouTubeMetadata

__all__ = [
    # Cookie Detection
    "ICookieDetector",
    "ICookieManager",
    "BrowserType",
    "PlatformType",
    # YouTube Metadata
    "IYouTubeMetadataService",
    "SubtitleInfo",
    "YouTubeMetadata",
    # Protocols
    "UIContextProtocol",
    "HasEventCoordinatorProtocol",
    "HasCleanupProtocol",
    "HasClearProtocol",
    "HasCompletedDownloadsProtocol",
    "TkRootProtocol",
    # Service Interfaces
    "IDownloadService",
    "IDownloadHandler",
    "ICookieHandler",
    "IMetadataService",
    "INetworkChecker",
    "IFileService",
    "IMessageQueue",
    "IErrorHandler",
    "IServiceFactory",
    "IAutoCookieManager",
    "IUIState",
    "BaseDownloader",
    # Exceptions
    "NetworkError",
    "AuthenticationError",
    "ServiceError",
]
