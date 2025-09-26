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

__all__ = [
    "IHandler",
    "IDownloadHandler",
    "IAuthenticationHandler",
    "IServiceDetector",
    "INetworkChecker",
    "IUIEventHandler",
    "IApplicationController",
    "ICookieDetector",
    "ICookieManager",
    "BrowserType",
    "PlatformType",
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
    "IDialogFactory"
]