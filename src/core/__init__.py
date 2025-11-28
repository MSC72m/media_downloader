"""Core application modules - shared primitives and application infrastructure."""

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

from .config import AppConfig, get_config, reset_config, set_config

def get_service_container():
    from src.application.di_container import ServiceContainer
    return ServiceContainer

def get_application_orchestrator():
    from src.application.orchestrator import ApplicationOrchestrator
    return ApplicationOrchestrator

__all__ = [
    "Download",
    "DownloadOptions",
    "ServiceType",
    "DownloadStatus",
    "UIState",
    "AuthState",
    "ButtonState",
    "DownloadResult",
    "AppConfig",
    "get_config",
    "set_config",
    "reset_config",
    "get_service_container",
    "get_application_orchestrator",
]
