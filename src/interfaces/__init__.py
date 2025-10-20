"""Abstraction layer interfaces for the media downloader application."""

from .handlers import (
    IHandler,
    IDownloadHandler,
    IAuthenticationHandler,
    IServiceDetector,
    INetworkChecker,
    IUIEventHandler,
    IApplicationController
)

from .cookie_detection import (
    ICookieDetector,
    ICookieManager,
    BrowserType,
    PlatformType
)

from .ui_components import (
    IUIComponent,
    IURLEntryComponent,
    IDownloadListComponent,
    IOptionsBarComponent,
    IActionButtonsComponent,
    IStatusBarComponent,
    IUIFactory,
    IDialog,
    INetworkStatusDialog,
    IFileManagerDialog,
    IDialogFactory
)

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
    "YouTubeSpecificHandler"
]
