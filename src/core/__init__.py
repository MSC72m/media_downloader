"""Core application modules - shared primitives and application infrastructure."""

# Models - All domain models
from .models import (
    Download, DownloadOptions, ServiceType, DownloadStatus, 
    UIState, AuthState, ButtonState, ConnectionResult, DownloadResult
)

# Base classes
from .base import BaseDownloader

# Application infrastructure
from .application.orchestrator import ApplicationOrchestrator
from .application.container import ServiceContainer

# Service management
from .services.accessor import ServiceAccessor
from .services.controller import ServiceController

__all__ = [
    # Models
    'Download',
    'DownloadOptions',
    'ServiceType',
    'DownloadStatus',
    'UIState',
    'AuthState',
    'ButtonState',
    'ConnectionResult',
    'DownloadResult',
    # Base
    'BaseDownloader',
    # Application
    'ApplicationOrchestrator',
    'ServiceContainer',
    # Services
    'ServiceAccessor',
    'ServiceController'
]
