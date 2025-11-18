"""Download Coordinator - Delegates all download operations to download_handler."""

from typing import Callable, List, Optional

from src.core.models import Download, DownloadStatus
from src.services.events.event_bus import DownloadEvent, DownloadEventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadCoordinator:
    """Coordinates download operations by delegating to download_handler."""

    def __init__(self, container, event_bus: DownloadEventBus):
        """Initialize with service container and event bus."""
        self.container = container
        self.event_bus = event_bus
        self._download_handler = None
        self.error_handler = None

        # Subscribe to download events
        self._setup_event_subscriptions()

    def refresh_handlers(self):
        """Refresh handler references from container."""
        self._download_handler = self.container.get("download_handler")
        self.error_handler = self.container.get("error_handler")
        logger.info("[DOWNLOAD_COORDINATOR] Handlers refreshed")

    # Component Access Helpers
    def _get_status_bar(self):
        """Get status bar component from container."""
        return self.container.get("status_bar")

    def _get_download_list(self):
        """Get download list component from container."""
        return self.container.get("download_list")

    def _get_action_buttons(self):
        """Get action buttons component from container."""
        return self.container.get("action_buttons")

    def _get_url_entry(self):
        """Get URL entry component from container."""
        return self.container.get("url_entry")

    def _update_status(self, message: str, is_error: bool = False):
        """Update status bar - helper to avoid repetition."""
        status_bar = self._get_status_bar()
        if not status_bar:
            logger.warning("[DOWNLOAD_COORDINATOR] Status bar not available")
            return

        if is_error:
            status_bar.show_error(message)
        else:
            status_bar.show_message(message)

    def _setup_event_subscriptions(self) -> None:
        """Subscribe to download events from event bus."""
        self.event_bus.subscribe(DownloadEvent.PROGRESS, self._on_progress_event)
        self.event_bus.subscribe(DownloadEvent.COMPLETED, self._on_completed_event)
        self.event_bus.subscribe(DownloadEvent.FAILED, self._on_failed_event)
        logger.info("[DOWNLOAD_COORDINATOR] Event subscriptions setup")

    # Event Handlers
    def _on_progress_event(
        self, download: Download, progress: float, speed: float
    ) -> None:
        """Handle progress event - update UI."""
        logger.debug(f"[DOWNLOAD_COORDINATOR] Progress: {download.name} - {progress}%")

        # Update download list
        download_list = self._get_download_list()
        if download_list:
            try:
                download_list.update_item_progress(download, progress)
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error updating progress: {e}")

        # Update status bar
        status_bar = self._get_status_bar()
        if status_bar:
            status_bar.show_message(f"Downloading {download.name}: {progress:.1f}%")

    def _on_completed_event(self, download: Download) -> None:
        """Handle completion event - update UI."""
        logger.info(f"[DOWNLOAD_COORDINATOR] Completed: {download.name}")

        # Refresh download list
        download_list = self._get_download_list()
        if download_list:
            try:
                download_list.refresh_items(download_list.get_downloads())
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

        # Enable action buttons
        action_buttons = self._get_action_buttons()
        if action_buttons:
            try:
                action_buttons.set_enabled(True)
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error enabling buttons: {e}")

        # Update status
        self._update_status(f"Download completed: {download.name}")

    def _on_failed_event(self, download: Download, error: str) -> None:
        """Handle failure event - update UI and show error dialog.

        SINGLE PATH: Show error dialog via message queue ONLY.
        Don't duplicate with status bar error.
        """
        logger.error(f"[DOWNLOAD_COORDINATOR] Failed: {download.name} - {error}")

        # Refresh download list
        download_list = self._get_download_list()
        if download_list:
            try:
                download_list.refresh_items(download_list.get_downloads())
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

        # Enable action buttons
        action_buttons = self._get_action_buttons()
        if action_buttons:
            try:
                action_buttons.set_enabled(True)
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error enabling buttons: {e}")

        # Update status bar with simple message (not error style)
        self._update_status(f"Download failed: {download.name}", is_error=False)

        # Show error via centralized error handler
        if self.error_handler:
            self.error_handler.show_error(
                "Download Failed", error or f"Failed to download: {download.name}"
            )

    # Download Management - All delegate to download_handler
    def add_download(self, download: Download) -> bool:
        """Add a download - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] download_handler not available")
            return False

        try:
            # Auto-clear completed downloads first
            cleared = self._auto_clear_completed_downloads()
            if cleared > 0:
                logger.info(
                    f"[DOWNLOAD_COORDINATOR] Auto-cleared {cleared} completed downloads"
                )

            # Set event bus on download for progress tracking
            download.set_event_bus(self.event_bus)

            # Delegate to download_handler
            self._download_handler.add_download(download)
            logger.info(f"[DOWNLOAD_COORDINATOR] Added download: {download.name}")

            # Update UI - add to download list
            download_list = self._get_download_list()
            if download_list:
                try:
                    download_list.add_download(download)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error adding to list: {e}")

            # Update status
            self._update_status(f"Download added: {download.name}")

            # Clear URL entry
            url_entry = self._get_url_entry()
            if url_entry:
                from src.utils.type_helpers import safe_clear

                safe_clear(url_entry)

            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to add download: {e}", exc_info=True
            )
            error_msg = f"Failed to add download: {str(e)}"
            # Show error via centralized error handler
            if self.error_handler:
                self.error_handler.show_error("Add Download Failed", error_msg)
            return False

    def remove_downloads(self, indices: List[int]) -> bool:
        """Remove downloads by indices - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] download_handler not available")
            return False

        try:
            # Delegate to download_handler
            self._download_handler.remove_downloads(indices)
            logger.info(f"[DOWNLOAD_COORDINATOR] Removed {len(indices)} downloads")

            # Update UI - refresh list
            download_list = self._get_download_list()
            if download_list:
                try:
                    download_list.refresh_items(download_list.get_downloads())
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

            # Update status
            self._update_status("Selected items removed")

            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to remove downloads: {e}", exc_info=True
            )
            error_msg = f"Failed to remove downloads: {str(e)}"
            # Show error via centralized error handler
            if self.error_handler:
                self.error_handler.show_error("Remove Downloads Failed", error_msg)
            return False

    def clear_downloads(self) -> bool:
        """Clear all downloads - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] download_handler not available")
            return False

        try:
            # Delegate to download_handler
            self._download_handler.clear_downloads()
            logger.info("[DOWNLOAD_COORDINATOR] Cleared all downloads")

            # Update UI - refresh list
            download_list = self._get_download_list()
            if download_list:
                try:
                    download_list.refresh_items(download_list.get_downloads())
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

            # Update status
            self._update_status("All items cleared")

            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to clear downloads: {e}", exc_info=True
            )
            error_msg = f"Failed to clear downloads: {str(e)}"
            # Show error via centralized error handler
            if self.error_handler:
                self.error_handler.show_error("Clear Downloads Failed", error_msg)
            return False

    def clear_completed_downloads(self) -> int:
        """Clear completed downloads - manual trigger."""
        try:
            download_list = self._get_download_list()
            if not download_list:
                return 0

            from src.utils.type_helpers import remove_completed_downloads

            count = remove_completed_downloads(download_list)

            # Early return for no items case
            if count == 0:
                self._update_status("No completed downloads to clear")
                return 0

            self._update_status(f"Cleared {count} completed download(s)")
            return count
        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to clear completed: {e}", exc_info=True
            )
            error_msg = f"Failed to clear completed downloads: {str(e)}"
            # Show error via centralized error handler
            if self.error_handler:
                self.error_handler.show_error("Clear Completed Failed", error_msg)
            return 0

    def _auto_clear_completed_downloads(self) -> int:
        """Auto-clear completed downloads (before adding new)."""
        download_list = self._get_download_list()
        if not download_list:
            return 0

        from src.utils.type_helpers import (
            has_completed_downloads,
            remove_completed_downloads,
        )

        if not has_completed_downloads(download_list):
            return 0

        count = remove_completed_downloads(download_list)
        logger.info(f"[DOWNLOAD_COORDINATOR] Auto-cleared {count} completed downloads")
        return count

    def start_downloads(self, download_dir: Optional[str] = None) -> bool:
        """Start all pending downloads - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] download_handler not available")
            return False

        try:
            # Check if there are items to download
            download_list = self._get_download_list()
            if not download_list or not download_list.has_items():
                self._update_status("Please add items to download")
                return False

            # Get downloads from download_handler (single source of truth)
            downloads = self._download_handler.get_downloads()
            if not downloads:
                self._update_status("No downloads available")
                return False

            logger.info(f"[DOWNLOAD_COORDINATOR] Starting {len(downloads)} downloads")

            # Set initial status on all downloads
            for download in downloads:
                download.status = DownloadStatus.DOWNLOADING
                download.progress = 0.0

            # Refresh UI to show updated status
            if download_list:
                try:
                    download_list.refresh_items(downloads)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

            # Define progress callback
            def on_progress(download: Download, progress: float) -> None:
                """Progress callback - download updates itself via event bus."""
                download.update_progress(progress, 0)

            # Disable buttons during download
            action_buttons = self._get_action_buttons()
            if action_buttons:
                try:
                    action_buttons.set_enabled(False)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error disabling buttons: {e}")

            self._update_status("Starting downloads...")

            # Get download directory
            if not download_dir:
                download_dir = self.container.get("downloads_folder")
                if not download_dir:
                    download_dir = "~/Downloads"

            # Delegate to download_handler - it handles everything
            self._download_handler.start_downloads(
                downloads=downloads,
                download_dir=download_dir,
                progress_callback=on_progress,
                completion_callback=None,  # We handle completion via events
            )

            logger.info("[DOWNLOAD_COORDINATOR] Downloads started successfully")
            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to start downloads: {e}", exc_info=True
            )
            error_msg = f"Failed to start downloads: {str(e)}"
            # Show error via centralized error handler
            if self.error_handler:
                self.error_handler.show_error("Start Downloads Failed", error_msg)

            # Re-enable buttons
            action_buttons = self._get_action_buttons()
            if action_buttons:
                try:
                    action_buttons.set_enabled(True)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error enabling buttons: {e}")

            return False

    # Query Methods
    def has_items(self) -> bool:
        """Check if there are any downloads."""
        if not self._download_handler:
            return False
        return self._download_handler.has_items()

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        if not self._download_handler:
            return False
        return self._download_handler.has_active_downloads()

    def get_downloads(self) -> List[Download]:
        """Get all downloads."""
        if not self._download_handler:
            return []
        return self._download_handler.get_downloads()
