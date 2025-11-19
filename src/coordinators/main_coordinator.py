"""Event Coordinator - Thin coordination layer using focused coordinators."""

from typing import Optional

import customtkinter as ctk

from src.services.detection.link_detector import LinkDetector
from src.services.events.event_bus import DownloadEventBus
from src.utils.logger import get_logger

from .download_coordinator import DownloadCoordinator
from .platform_dialog_coordinator import PlatformDialogCoordinator

logger = get_logger(__name__)


class EventCoordinator:
    """Event coordinator - thin routing layer for platform-specific operations.

    This is a THIN coordination layer that:
    1. Exposes downloads (DownloadCoordinator) for download operations
    2. Exposes platform_dialogs (PlatformDialogCoordinator) for platform dialogs
    3. Provides routing methods with business logic (platform_download, cookie_detected)
    4. Does NOT contain unnecessary wrapper methods

    Usage:
        - For downloads: coord.downloads.add_download(), coord.downloads.start_downloads()
        - For platform dialogs: coord.platform_dialogs.show_youtube_dialog()
        - For routing: coord.platform_download(), coord.cookie_detected()
    """

    def __init__(self, root_window: ctk.CTk, container):
        """Initialize with root window and service container."""
        self.root = root_window
        self.container = container
        self.error_handler = None

        # Event bus for download events
        self.event_bus = DownloadEventBus(root_window)

        # Link detector for URL detection
        self.link_detector = LinkDetector()

        # Create focused coordinators
        self.downloads = DownloadCoordinator(container, self.event_bus)
        self.platform_dialogs = PlatformDialogCoordinator(container, root_window)

        logger.info("[EVENT_COORDINATOR] Initialized with focused coordinators")

    def refresh_handlers(self) -> None:
        """Refresh all handlers after UI components are registered."""
        logger.info("[EVENT_COORDINATOR] Refreshing handlers")
        self.downloads.refresh_handlers()
        self.platform_dialogs.refresh_handlers()
        self.error_handler = self.container.get("error_handler")
        logger.info("[EVENT_COORDINATOR] Handlers refreshed")

    def show_error(self, title: str, message: str) -> None:
        """Show error message via centralized error handler."""
        if not self.error_handler:
            logger.error(
                f"[EVENT_COORDINATOR] Error handler not available: {title}: {message}"
            )
            return

        self.error_handler.show_error(title, message)

    # Platform-Specific Dialogs - Single dispatch method
    def platform_download(
        self, platform: str, url: str, name: Optional[str] = None
    ) -> None:
        """Dispatch platform-specific download dialog.

        Args:
            platform: Platform type (youtube, twitter, instagram, pinterest, generic)
            url: URL to download
            name: Optional name for generic downloads
        """
        # YouTube handler manages its own dialogs - just provide add_download callback
        if platform == "youtube":
            logger.warning(
                "[EVENT_COORDINATOR] YouTube handler should manage dialogs directly, "
                "coordinator should not be in the flow"
            )
            return

        platform_map = {
            "twitter": self.platform_dialogs.show_twitter_dialog,
            "instagram": self.platform_dialogs.show_instagram_dialog,
            "pinterest": self.platform_dialogs.show_pinterest_dialog,
            "soundcloud": self.platform_dialogs.show_soundcloud_dialog,
            "generic": self.platform_dialogs.generic_download,
        }

        dialog_method = platform_map.get(platform)
        if not dialog_method:
            logger.error(f"[EVENT_COORDINATOR] Unknown platform: {platform}")
            return

        callback = lambda download: self.downloads.add_download(download)

        if platform == "generic":
            dialog_method(url, name, callback)
        else:
            dialog_method(url, callback)

    # Authentication
    def authenticate_instagram(self, parent_window) -> None:
        """Show Instagram authentication dialog - delegates to platform coordinator."""
        self.platform_dialogs.authenticate_instagram(parent_window)

    # UI Dialogs
    def show_file_manager(self) -> None:
        """Show file manager dialog."""
        try:
            from src.ui.dialogs.file_manager_dialog import FileManagerDialog

            downloads_folder = self.container.get("downloads_folder") or "~/Downloads"
            status_bar = self.container.get("status_bar")

            def on_directory_change(path: str) -> None:
                """Update downloads folder when user selects new path."""
                self.container.register("downloads_folder", path, singleton=True)
                logger.info(f"[EVENT_COORDINATOR] Downloads folder updated to: {path}")

            FileManagerDialog(
                self.root,
                downloads_folder,
                on_directory_change,
                lambda msg: status_bar.show_message(msg) if status_bar else None,
            )
        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error showing file manager: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "File Manager Error", f"Failed to open file manager: {str(e)}"
                )

    def show_network_status(self) -> None:
        """Show network status dialog."""
        network_checker = self.container.get("network_checker")
        if not network_checker:
            if self.error_handler:
                self.error_handler.show_error(
                    "Network Status", "Network checker not available"
                )
            return

        try:
            from src.ui.dialogs.network_status_dialog import NetworkStatusDialog

            NetworkStatusDialog(self.root, network_checker)
        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error showing network status: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "Network Status Error",
                    f"Failed to open network status dialog: {str(e)}",
                )

    # Cookie Detection
    def cookie_detected(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection."""
        cookie_handler = self.container.get("cookie_handler")
        if not cookie_handler:
            return

        try:
            if not cookie_handler.set_cookie_file(cookie_path):
                if self.error_handler:
                    self.error_handler.show_error(
                        "Cookie Error", "Failed to load cookie file"
                    )
                return

            status_bar = self.container.get("status_bar")
            if status_bar:
                status_bar.show_message(f"Cookie loaded from {browser_type}")
        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error handling cookie: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "Cookie Error", f"Error loading cookie: {str(e)}"
                )

    # UIContextProtocol implementation via __getattr__ for dynamic dispatch
    def __getattr__(self, name: str):
        """Dynamic dispatch for platform_download methods.

        Handles calls like youtube_download, twitter_download, etc.
        by routing to platform_download with the appropriate platform name.
        """
        platform_methods = {
            "youtube_download": "youtube",
            "twitter_download": "twitter",
            "instagram_download": "instagram",
            "pinterest_download": "pinterest",
            "soundcloud_download": "soundcloud",
        }

        if name in platform_methods:
            platform = platform_methods[name]
            # YouTube handler creates dialogs itself, just needs add_download callback
            if platform == "youtube":
                return lambda download: self.downloads.add_download(download)
            return lambda url, **kwargs: self.platform_download(
                platform, url, kwargs.get("name")
            )

        if name == "generic_download":
            return lambda url, name=None: self.platform_download("generic", url, name)

        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )
