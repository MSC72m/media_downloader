"""Event Coordinator - Thin coordination layer using focused coordinators."""

from typing import List, Optional

import customtkinter as ctk

from src.core.models import Download
from src.services.detection.link_detector import LinkDetector
from src.services.events.event_bus import DownloadEventBus
from src.utils.logger import get_logger

from .download_coordinator import DownloadCoordinator
from .platform_dialog_coordinator import PlatformDialogCoordinator
from .ui_state_manager import UIStateManager

logger = get_logger(__name__)


class EventCoordinator:
    """Event coordinator - delegates to focused coordinators.

    This is a THIN coordination layer that:
    1. Uses UIStateManager for all UI updates
    2. Uses DownloadCoordinator for all download operations
    3. Uses PlatformDialogCoordinator for platform-specific dialogs
    4. Does NOT contain business logic
    5. Does NOT duplicate handler logic
    """

    def __init__(self, root_window: ctk.CTk, container):
        """Initialize with root window and service container."""
        self.root = root_window
        self.container = container

        # Event bus for download events
        self.event_bus = DownloadEventBus(root_window)

        # Link detector for URL detection
        self.link_detector = LinkDetector()

        # Create focused coordinators
        self.ui_state = UIStateManager(container)
        self.downloads = DownloadCoordinator(container, self.event_bus, self.ui_state)
        self.platform_dialogs = PlatformDialogCoordinator(container, root_window)

        logger.info("[EVENT_COORDINATOR] Initialized with focused coordinators")

    def refresh_handlers(self) -> None:
        """Refresh all handlers after UI components are registered."""
        logger.info("[EVENT_COORDINATOR] Refreshing handlers")
        self.ui_state.refresh_ui_components()
        self.downloads.refresh_handlers()
        self.platform_dialogs.refresh_handlers()
        logger.info("[EVENT_COORDINATOR] Handlers refreshed")

    # Download Management - Delegate to DownloadCoordinator
    def add_download(self, download: Download) -> bool:
        """Add a download - delegates to download coordinator."""
        return self.downloads.add_download(download)

    def remove_downloads(self, indices: List[int]) -> bool:
        """Remove downloads - delegates to download coordinator."""
        return self.downloads.remove_downloads(indices)

    def clear_downloads(self) -> bool:
        """Clear all downloads - delegates to download coordinator."""
        return self.downloads.clear_downloads()

    def start_downloads(self) -> bool:
        """Start downloads - delegates to download coordinator."""
        return self.downloads.start_downloads()

    def clear_completed_downloads(self) -> int:
        """Clear completed downloads - delegates to download coordinator."""
        return self.downloads.clear_completed_downloads()

    # UI Updates - Delegate to UIStateManager
    def update_status(self, message: str, is_error: bool = False) -> None:
        """Update status bar - delegates to UI state manager."""
        self.ui_state.update_status(message, is_error)

    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        """Update button states - delegates to UI state manager."""
        self.ui_state.update_button_states(has_selection, has_items)

    def show_error(self, title: str, message: str) -> None:
        """Show error message - uses message queue for proper error dialogs."""
        try:
            from src.core.enums.message_level import MessageLevel
            from src.services.events.queue import Message

            message_queue = self.container.get("message_queue")
            if message_queue:
                error_message = Message(
                    text=message, level=MessageLevel.ERROR, title=title
                )
                message_queue.add_message(error_message)
            else:
                # Fallback to status bar
                self.ui_state.show_error(f"{title}: {message}")
        except Exception as e:
            # Ultimate fallback
            logger.error(f"Error showing error dialog: {e}")
            self.ui_state.show_error(f"{title}: {message}")

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
            dialog_method(url, name, lambda download: self.add_download(download))
            return

        dialog_method(url, lambda download: self.add_download(download))
        return

    # Convenience methods for backward compatibility
    def youtube_download(self, url: str, **kwargs) -> None:
        self.platform_download("youtube", url)

    def twitter_download(self, url: str, **kwargs) -> None:
        self.platform_download("twitter", url)

    def instagram_download(self, url: str, **kwargs) -> None:
        self.platform_download("instagram", url)

    def pinterest_download(self, url: str, **kwargs) -> None:
        self.platform_download("pinterest", url)

    def soundcloud_download(self, url: str, **kwargs) -> None:
        self.platform_download("soundcloud", url)

    def generic_download(self, url: str, name: Optional[str] = None) -> None:
        self.platform_download("generic", url, name)

    def authenticate_instagram(self, parent_window=None) -> None:
        """Show Instagram authentication - delegates to platform dialog coordinator."""
        self.platform_dialogs.authenticate_instagram(parent_window)

    # File Management
    def show_file_manager(self) -> None:
        """Show file manager dialog."""
        try:
            from src.ui.dialogs.file_manager_dialog import FileManagerDialog

            downloads_folder = self.container.get("downloads_folder")

            def on_dir_change(path: str) -> None:
                self.set_download_directory(path)

            FileManagerDialog(
                self.root,
                downloads_folder,
                on_directory_change=on_dir_change,
                show_status=lambda msg: self.ui_state.update_status(msg),
            )
            logger.info("[EVENT_COORDINATOR] File manager shown")
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error showing file manager: {e}",
                exc_info=True,
            )
            self.ui_state.show_error(f"Failed to open file manager: {str(e)}")

    def browse_files(self, file_types: Optional[List[str]] = None) -> Optional[str]:
        """Browse for files."""
        try:
            from tkinter import filedialog

            filetypes = []
            if file_types:
                for file_type in file_types:
                    filetypes.append((f"{file_type} files", f"*.{file_type}"))
            filetypes.append(("All files", "*.*"))

            file_path = filedialog.askopenfilename(
                parent=self.root, title="Select File", filetypes=filetypes
            )
            return file_path if file_path else None
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error browsing files: {e}",
                exc_info=True,
            )
            return None

    # Configuration
    def get_download_directory(self) -> str:
        """Get download directory from container."""
        downloads_folder = self.container.get("downloads_folder")
        return downloads_folder if downloads_folder else "~/Downloads"

    def set_download_directory(self, directory: str) -> bool:
        """Set download directory in container."""
        try:
            import os

            expanded_dir = os.path.expanduser(directory)
            os.makedirs(expanded_dir, exist_ok=True)
            self.container.register("downloads_folder", expanded_dir, singleton=True)
            logger.info(f"[EVENT_COORDINATOR] Download directory set: {expanded_dir}")
            return True
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error setting download directory: {e}",
                exc_info=True,
            )
            return False

    # Network Status
    def show_network_status(self) -> None:
        """Show network status dialog."""
        try:
            from src.ui.dialogs.network_status_dialog import NetworkStatusDialog

            NetworkStatusDialog(self.root)
            logger.info("[EVENT_COORDINATOR] Network status shown")
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error showing network status: {e}",
                exc_info=True,
            )

    # Cookie Detection
    def cookie_detected(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection."""
        logger.info(
            f"[EVENT_COORDINATOR] Cookie detected: {browser_type} at {cookie_path}"
        )
        try:
            cookie_handler = self.container.get("cookie_handler")
            if cookie_handler:
                success = cookie_handler.set_cookie_file(cookie_path)
                if success:
                    self.ui_state.update_status(f"Cookie loaded from {browser_type}")
                else:
                    self.ui_state.show_error("Failed to load cookie file")
            else:
                logger.warning("[EVENT_COORDINATOR] Cookie handler not available")
        except Exception as e:
            logger.error(
                f"[EVENT_COORDINATOR] Error handling cookie detection: {e}",
                exc_info=True,
            )
            self.ui_state.show_error(f"Error loading cookie: {str(e)}")
