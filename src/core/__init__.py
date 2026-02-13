import importlib
from typing import Any

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


def _load_symbol(module_path: str, symbol_name: str) -> Any:
    module = importlib.import_module(module_path)
    return getattr(module, symbol_name)


def get_service_container():
    return _load_symbol("src.application.di_container", "ServiceContainer")


def get_application_orchestrator():
    return _load_symbol("src.application.orchestrator", "ApplicationOrchestrator")


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
