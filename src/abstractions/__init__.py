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