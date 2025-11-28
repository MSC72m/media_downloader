"""Core application modules - shared primitives and application infrastructure."""

from .config import AppConfig, get_config, reset_config, set_config
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


def get_service_container():
    from src.application.di_container import ServiceContainer

    return ServiceContainer


def get_application_orchestrator():
    from src.application.orchestrator import ApplicationOrchestrator

    return ApplicationOrchestrator


__all__ = [
    "AppConfig",
    "AuthState",
    "ButtonState",
    "ConnectionResult",
    "Download",
    "DownloadOptions",
    "DownloadResult",
    "DownloadStatus",
    "ServiceType",
    "UIState",
    "get_application_orchestrator",
    "get_config",
    "get_service_container",
    "reset_config",
    "set_config",
]
