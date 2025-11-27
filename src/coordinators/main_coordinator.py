"""Event Coordinator - Clean coordination layer with constructor injection."""

from typing import Optional, Callable

import customtkinter as ctk

from src.core.interfaces import (
    IErrorHandler,
    IDownloadHandler,
    IFileService,
    INetworkChecker,
    ICookieHandler,
    IDownloadService,
    IMessageQueue,
)
from src.services.detection.link_detector import LinkDetector
from src.services.events.event_bus import DownloadEventBus
from src.ui.dialogs.file_manager_dialog import FileManagerDialog
from src.ui.dialogs.network_status_dialog import NetworkStatusDialog
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

    def __init__(self, root_window: ctk.CTk, error_handler: IErrorHandler,
                 download_handler: IDownloadHandler, file_service: IFileService,
                 network_checker: INetworkChecker, cookie_handler: ICookieHandler,
                 download_service: IDownloadService, message_queue: Optional[IMessageQueue] = None,
                 downloads_folder: str = "~/Downloads"):
        """Initialize with proper dependency injection."""
        self.root = root_window
        self.error_handler = error_handler
        self.download_handler = download_handler
        self.file_service = file_service
        self.network_checker = network_checker
        self.cookie_handler = cookie_handler
        self.download_service = download_service
        self.message_queue = message_queue
        self.downloads_folder = downloads_folder

        # Event bus for download events
        self.event_bus = DownloadEventBus(root_window)

        # Link detector will be set by orchestrator after initialization
        # Don't create here to avoid duplicate instances
        self.link_detector = None

        # Create focused coordinators with injected dependencies
        self.downloads = DownloadCoordinator(
            event_bus=self.event_bus,
            download_handler=download_handler,
            error_handler=self.error_handler,
            download_service=self.download_service,
            message_queue=self.message_queue,
        )
        # Platform dialog coordinator needs orchestrator reference for UI components
        # We'll set it after orchestrator is fully initialized
        self.platform_dialogs = PlatformDialogCoordinator(root_window, error_handler, cookie_handler, orchestrator=None)

        logger.info("[EVENT_COORDINATOR] Initialized with constructor injection")

    def refresh_handlers(self) -> None:
        """Refresh all handlers after UI components are registered."""
        logger.info("[EVENT_COORDINATOR] Refreshing handlers")
        # No refresh needed - coordinators use constructor injection with mandatory dependencies
        logger.info("[EVENT_COORDINATOR] Handlers refreshed")

    def set_message_queue(self, message_queue: IMessageQueue) -> None:
        """Set message queue instance for late binding."""
        self.message_queue = message_queue
        if self.downloads:
            self.downloads.set_message_queue(message_queue)
        logger.info("[EVENT_COORDINATOR] Message queue updated")

    def set_ui_callbacks(self, callbacks: dict[str, Callable]) -> None:
        """Set UI callbacks for download coordinator."""
        if self.downloads:
            self.downloads.set_ui_callbacks(callbacks)
        logger.info("[EVENT_COORDINATOR] UI callbacks propagated to download coordinator")

    def show_error(self, title: str, message: str) -> None:
        """Show error message via centralized error handler."""
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
            return None

        dialog_method(url, callback)
        return None

    # Authentication
    def authenticate_instagram(self, parent_window, callback=None) -> None:
        """Show Instagram authentication dialog - delegates to platform coordinator.
        
        Args:
            parent_window: Parent window for dialogs
            callback: Optional callback to update button state (receives InstagramAuthStatus)
        """
        self.platform_dialogs.authenticate_instagram(parent_window, callback)

    # UI Dialogs
    def show_file_manager(self) -> None:
        """Show file manager dialog."""
        try:
            def on_directory_change(path: str) -> None:
                """Update downloads folder when user selects new path."""
                # Note: In a perfect system, this would go through a config service
                # For now, updating local state since this is UI-specific
                self.downloads_folder = path
                logger.info(f"[EVENT_COORDINATOR] Downloads folder updated to: {path}")

            FileManagerDialog(
                self.root,
                self.downloads_folder,
                on_directory_change,
                lambda msg: self.error_handler.show_info("File Manager", msg),
            )
        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error showing file manager: {e}")
            self.error_handler.show_error(
                "File Manager Error", f"Failed to open file manager: {str(e)}"
            )

    def show_network_status(self) -> None:
        """Show network status dialog."""
        try:
            NetworkStatusDialog(self.root, self.network_checker)
        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error showing network status: {e}")
            self.error_handler.show_error(
                "Network Status Error",
                f"Failed to open network status dialog: {str(e)}",
            )

    # Cookie Detection
    def cookie_detected(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection."""
        try:
            if not self.cookie_handler.set_cookie_file(cookie_path):
                self.error_handler.show_error(
                    "Cookie Error", "Failed to load cookie file"
                )
                return

            logger.info(f"[EVENT_COORDINATOR] Cookie loaded from {browser_type}")
        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error handling cookie: {e}")

    # Connectivity Check
    def check_connectivity(self) -> None:
        """Check network connectivity and show status."""
        try:
            is_connected, error_message = self.network_checker.check_connectivity()

            if is_connected:
                logger.info("[EVENT_COORDINATOR] Connectivity check: Connected")
                if self.message_queue:
                    from src.core.models import Message
                    from src.core.enums.message_level import MessageLevel
                    message = Message(
                        text="Network connection is working",
                        level=MessageLevel.INFO,
                        title="Network Status"
                    )
                    self.message_queue.add_message(message)
            else:
                logger.warning(f"[EVENT_COORDINATOR] Connectivity check failed: {error_message}")
                if self.message_queue:
                    from src.core.models import Message
                    from src.core.enums.message_level import MessageLevel
                    message = Message(
                        text=f"Network issue: {error_message}",
                        level=MessageLevel.WARNING,
                        title="Network Issue"
                    )
                    self.message_queue.add_message(message)

                # Show network status dialog for detailed information
                self.show_network_status()

        except Exception as e:
            logger.error(f"[EVENT_COORDINATOR] Error checking connectivity: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "Connectivity Check Error",
                    f"Failed to check network connectivity: {str(e)}"
                )
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
