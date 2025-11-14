"""Abstraction layer interfaces for the media downloader application."""

from .cookie_detection import BrowserType, ICookieDetector, ICookieManager, PlatformType
from .event_handlers import (
    AuthenticationHandler,
    ConfigurationHandler,
    DownloadManagementHandler,
    FileManagementHandler,
    NetworkStatusHandler,
    UIUpdateHandler,
    URLDetectionHandler,
    YouTubeSpecificHandler,
)
from .handlers import (
    IApplicationController,
    IAuthenticationHandler,
    IDownloadHandler,
    IHandler,
    INetworkChecker,
    IServiceDetector,
    IUIEventHandler,
)
from .ui_components import (
    IActionButtonsComponent,
    IDialog,
    IDialogFactory,
    IDownloadListComponent,
    IFileManagerDialog,
    INetworkStatusDialog,
    IOptionsBarComponent,
    IStatusBarComponent,
    IUIComponent,
    IUIFactory,
    IURLEntryComponent,
)

__all__ = [
    # Handlers
    "IHandler",
    "IDownloadHandler",
    "IAuthenticationHandler",
    "IServiceDetector",
    "INetworkChecker",
    "IUIEventHandler",
    "IApplicationController",
    # Cookie
    "ICookieDetector",
    "ICookieManager",
    "BrowserType",
    "PlatformType",
    # UI Components
    "IUIComponent",
    "IURLEntryComponent",
    "IDownloadListComponent",
    "IOptionsBarComponent",
    "IActionButtonsComponent",
    "IStatusBarComponent",
    "IUIFactory",
    "IDialog",
    "INetworkStatusDialog",
    "IFileManagerDialog",
    "IDialogFactory",
    # Event Handlers
    "URLDetectionHandler",
    "DownloadManagementHandler",
    "UIUpdateHandler",
    "AuthenticationHandler",
    "FileManagementHandler",
    "ConfigurationHandler",
    "NetworkStatusHandler",
    "YouTubeSpecificHandler",
]
