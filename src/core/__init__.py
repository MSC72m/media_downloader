"""Core application modules - shared primitives and application infrastructure."""

# Models - All domain models
from .application.container import ServiceContainer

# Application infrastructure
from .application.orchestrator import ApplicationOrchestrator

# Base classes
from .base import BaseDownloader
from .models import (
    AuthState,
    ButtonState,
    ConnectionResult,
    Download,
    DownloadOptions,
    DownloadResult,
    DownloadStatus,
    ServiceType,
    UIState,
)

__all__ = [
    # Models
    "Download",
    "DownloadOptions",
    "ServiceType",
    "DownloadStatus",
    "UIState",
    "AuthState",
    "ButtonState",
    "ConnectionResult",
    "DownloadResult",
    # Base
    "BaseDownloader",
    # Application
    "ApplicationOrchestrator",
    "ServiceContainer",
]
