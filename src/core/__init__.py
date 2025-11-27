"""Core application modules - shared primitives and application infrastructure."""

# Models - All domain models
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

# Base classes
from .base.base_handler import BaseHandler  # Handler classes from base/ package
from .base.user_notifier import BaseUserNotifier

# Configuration
from .config import AppConfig, get_config, reset_config, set_config

# Application infrastructure - lazy import to avoid circular dependencies
def get_service_container():
    """Get service container - lazy import to avoid circular dependencies."""
    from .application.di_container import ServiceContainer
    return ServiceContainer

def get_application_orchestrator():
    """Get application orchestrator - lazy import to avoid circular dependencies."""
    from .application.orchestrator import ApplicationOrchestrator
    return ApplicationOrchestrator

__all__ = [
    # Models
    "Download",
    "DownloadOptions",
    "ServiceType",
    "DownloadStatus",
    "UIState",
    "AuthState",
    "ButtonState",
    "DownloadResult",
    # Configuration
    "AppConfig",
    "get_config",
    "set_config",
    "reset_config",
    # Application factories (lazy)
    "get_service_container",
    "get_application_orchestrator",
]
