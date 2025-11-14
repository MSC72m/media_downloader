"""Coordinators package - Simple, focused coordinators following KISS and SOLID."""

from .download_coordinator import DownloadCoordinator
from .main_coordinator import EventCoordinator
from .platform_dialog_coordinator import PlatformDialogCoordinator
from .ui_state_manager import UIStateManager

__all__ = [
    "DownloadCoordinator",
    "EventCoordinator",
    "PlatformDialogCoordinator",
    "UIStateManager",
]
