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
        logger.info(f"[EVENT_COORDINATOR] {platform} download: {url}")

        platform_map = {
            "youtube": self.platform_dialogs.show_youtube_dialog,
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

        # Generic download needs name parameter
        if platform == "generic":
            dialog_method(
                url, name, lambda download: self.downloads.add_download(download)
            )
            return

        dialog_method(url, lambda download: self.downloads.add_download(download))
        return

    # Authentication
    def authenticate_instagram(self, parent_window) -> None:
        """Show Instagram authentication dialog - delegates to platform coordinator."""
        self.platform_dialogs.authenticate_instagram(parent_window)

    # UI Dialogs
    def show_file_manager(self) -> None:
        """Show file manager dialog."""
        try:
            from src.ui.dialogs.file_manager_dialog import FileManagerDialog

            downloads_folder = self.container.get("downloads_folder")
            if not downloads_folder:
                downloads_folder = "~/Downloads"

            # Get status bar for showing messages
            status_bar = self.container.get("status_bar")

            def on_directory_change(new_path: str) -> None:
                """Handle directory change in file manager."""
                logger.info(f"[EVENT_COORDINATOR] Directory changed to: {new_path}")
                # Could update container's downloads_folder here if needed

            def show_status(message: str) -> None:
                """Show status message from file manager."""
                if status_bar:
                    status_bar.show_message(message)

            dialog = FileManagerDialog(
                self.root, downloads_folder, on_directory_change, show_status
            )
            logger.info("[EVENT_COORDINATOR] File manager dialog shown")
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error showing file manager: {e}", exc_info=True
            )
            if self.error_handler:
                self.error_handler.show_error(
                    "File Manager Error", f"Failed to open file manager: {str(e)}"
                )

    def show_network_status(self) -> None:
        """Show network status dialog."""
        try:
            from src.ui.dialogs.network_status_dialog import NetworkStatusDialog

            network_checker = self.container.get("network_checker")
            if not network_checker:
                logger.warning("[EVENT_COORDINATOR] Network checker not available")
                if self.error_handler:
                    self.error_handler.show_error(
                        "Network Status", "Network checker not available"
                    )
                return

            dialog = NetworkStatusDialog(self.root, network_checker)
            logger.info("[EVENT_COORDINATOR] Network status dialog shown")
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error showing network status: {e}", exc_info=True
            )
            if self.error_handler:
                self.error_handler.show_error(
                    "Network Status Error",
                    f"Failed to open network status dialog: {str(e)}",
                )

    # Cookie Detection
    def cookie_detected(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection."""
        logger.info(
            f"[EVENT_COORDINATOR] Cookie detected: {browser_type} at {cookie_path}"
        )
        try:
            cookie_handler = self.container.get("cookie_handler")
            if not cookie_handler:
                logger.warning("[EVENT_COORDINATOR] Cookie handler not available")
                return None

            success = cookie_handler.set_cookie_file(cookie_path)
            if not success:
                if self.error_handler:
                    self.error_handler.show_error(
                        "Cookie Error", "Failed to load cookie file"
                    )
                return None

            # Update status bar
            status_bar = self.container.get("status_bar")
            if status_bar:
                status_bar.show_message(f"Cookie loaded from {browser_type}")
            return None
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error handling cookie detection: {e}",
                exc_info=True,
            )
            if self.error_handler:
                self.error_handler.show_error(
                    "Cookie Error", f"Error loading cookie: {str(e)}"
                )

    # Platform-specific download methods (UIContextProtocol implementation)
    def youtube_download(self, url: str, **kwargs) -> None:
        """Handle YouTube download - implements UIContextProtocol."""
        self.platform_download("youtube", url)

    def twitter_download(self, url: str, **kwargs) -> None:
        """Handle Twitter download - implements UIContextProtocol."""
        self.platform_download("twitter", url)

    def instagram_download(self, url: str, **kwargs) -> None:
        """Handle Instagram download - implements UIContextProtocol."""
        self.platform_download("instagram", url)

    def pinterest_download(self, url: str, **kwargs) -> None:
        """Handle Pinterest download - implements UIContextProtocol."""
        self.platform_download("pinterest", url)

    def soundcloud_download(self, url: str, **kwargs) -> None:
        """Handle SoundCloud download - implements UIContextProtocol."""
        self.platform_download("soundcloud", url)

    def generic_download(self, url: str, name: Optional[str] = None) -> None:
        """Handle generic download - implements UIContextProtocol."""
        self.platform_download("generic", url, name)
