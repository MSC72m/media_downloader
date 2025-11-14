"""UI State Manager - Handles all UI state updates."""

from typing import List, Optional

from src.core.models import Download
from src.utils.logger import get_logger
from src.utils.type_helpers import (
    has_completed_downloads,
    remove_completed_downloads,
    safe_clear,
)

logger = get_logger(__name__)


class UIStateManager:
    """Manages UI state updates - buttons, status bar, progress, download list."""

    def __init__(self, container):
        """Initialize with service container to get UI components."""
        self.container = container
        self._download_list = None
        self._status_bar = None
        self._action_buttons = None
        self._url_entry = None

    def refresh_ui_components(self):
        """Refresh UI component references from container."""
        self._download_list = self.container.get("download_list")
        self._status_bar = self.container.get("status_bar")
        self._action_buttons = self.container.get("action_buttons")
        self._url_entry = self.container.get("url_entry")
        logger.info("[UI_STATE_MANAGER] UI components refreshed")

    # Status Bar Updates
    def update_status(self, message: str, is_error: bool = False) -> None:
        """Update status bar message."""
        if not self._status_bar:
            logger.debug("[UI_STATE_MANAGER] Status bar not available")
            return

        if is_error:
            self._status_bar.show_error(message)
        else:
            self._status_bar.show_message(message)

    def show_error(self, message: str) -> None:
        """Show error message in status bar."""
        self.update_status(message, is_error=True)

    # Progress Updates
    def update_progress(self, download: Download, progress: float) -> None:
        """Update download progress in UI."""
        if not download:
            logger.warning("[UI_STATE_MANAGER] Download object is None")
            return

        # Clamp progress to valid range
        progress = max(0.0, min(100.0, float(progress)))

        # Update download list
        if self._download_list:
            try:
                self._download_list.update_item_progress(download, progress)
            except Exception as e:
                logger.error(f"[UI_STATE_MANAGER] Error updating download list: {e}")

        # Update status bar
        if self._status_bar:
            self._status_bar.show_message(
                f"Downloading {download.name}: {progress:.1f}%"
            )

    # Download List Updates
    def refresh_download_list(self, downloads: Optional[List[Download]] = None) -> None:
        """Refresh the download list display."""
        if not self._download_list:
            logger.debug("[UI_STATE_MANAGER] Download list not available")
            return

        try:
            if downloads is None:
                downloads = self._download_list.get_downloads()
            self._download_list.refresh_items(downloads)
            logger.debug("[UI_STATE_MANAGER] Download list refreshed")
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error refreshing download list: {e}")

    def add_download_to_list(self, download: Download) -> bool:
        """Add download to the UI list."""
        if not self._download_list:
            logger.error("[UI_STATE_MANAGER] Download list not available")
            return False

        try:
            self._download_list.add_download(download)
            logger.info(f"[UI_STATE_MANAGER] Added download to list: {download.name}")
            return True
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error adding download to list: {e}")
            return False

    def clear_url_entry(self) -> None:
        """Clear the URL entry field."""
        if self._url_entry:
            safe_clear(self._url_entry)
            logger.debug("[UI_STATE_MANAGER] URL entry cleared")

    # Button State Management
    def enable_action_buttons(self) -> None:
        """Enable all action buttons."""
        if not self._action_buttons:
            logger.debug("[UI_STATE_MANAGER] Action buttons not available")
            return

        try:
            self._action_buttons.set_enabled(True)
            logger.debug("[UI_STATE_MANAGER] Action buttons enabled")
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error enabling buttons: {e}")

    def disable_action_buttons(self) -> None:
        """Disable all action buttons."""
        if not self._action_buttons:
            logger.debug("[UI_STATE_MANAGER] Action buttons not available")
            return

        try:
            self._action_buttons.set_enabled(False)
            logger.debug("[UI_STATE_MANAGER] Action buttons disabled")
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error disabling buttons: {e}")

    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        """Update button states based on selection and items."""
        if not self._action_buttons:
            logger.debug("[UI_STATE_MANAGER] Action buttons not available")
            return

        try:
            self._action_buttons.update_states(has_selection, has_items)
            logger.debug(
                f"[UI_STATE_MANAGER] Button states updated: selection={has_selection}, items={has_items}"
            )
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error updating button states: {e}")

    # Completion Handling
    def handle_download_completion(self, success: bool, message: str) -> None:
        """Handle download completion - update UI state."""
        logger.info(
            f"[UI_STATE_MANAGER] Handling completion: success={success}, message={message}"
        )

        # Re-enable buttons
        self.enable_action_buttons()

        # Refresh download list
        self.refresh_download_list()

        # Show completion message
        if success:
            self.update_status(message or "Downloads completed!")
        else:
            self.show_error(message or "Download failed")

    # Helper Methods
    def get_download_list(self):
        """Get the download list component."""
        return self._download_list

    def get_selected_indices(self) -> List[int]:
        """Get selected indices from download list."""
        if not self._download_list:
            return []
        try:
            return self._download_list.get_selected_indices()
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error getting selected indices: {e}")
            return []

    def has_items(self) -> bool:
        """Check if download list has items."""
        if not self._download_list:
            return False
        try:
            return self._download_list.has_items()
        except Exception as e:
            logger.error(f"[UI_STATE_MANAGER] Error checking items: {e}")
            return False

    def has_completed_downloads(self) -> bool:
        """Check if there are completed downloads."""
        if not self._download_list:
            return False
        return has_completed_downloads(self._download_list)

    def remove_completed_downloads(self) -> int:
        """Remove completed downloads from list."""
        if not self._download_list:
            return 0
        count = remove_completed_downloads(self._download_list)
        if count > 0:
            logger.info(f"[UI_STATE_MANAGER] Removed {count} completed downloads")
        return count
