"""Download Coordinator - Delegates all download operations to download_handler."""

from typing import List, Optional

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

    def _update_status(self, message: str, is_error: bool = False):
        """Update status bar - helper to avoid repetition."""
        status_bar = self.container.get("status_bar")
        if not status_bar:
            logger.warning("[DOWNLOAD_COORDINATOR] Status bar not available")
            return

        if not is_error:
            status_bar.show_error(message)
        else:
            status_bar.show_message(message)

    def _refresh_ui_after_event(self, enable_buttons: bool = True) -> None:
        """Refresh UI components after download event."""
        download_list = self.container.get("download_list")
        download_service = self.container.get("download_service")

        if download_list and download_service:
            try:
                # Get downloads from the service (source of truth), not from the list
                downloads = download_service.get_downloads()
                download_list.refresh_items(downloads)
                logger.debug(
                    f"[DOWNLOAD_COORDINATOR] Refreshed UI with {len(downloads)} downloads"
                )
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

        if enable_buttons:
            action_buttons = self.container.get("action_buttons")
            if action_buttons:
                try:
                    action_buttons.set_enabled(True)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error enabling buttons: {e}")

    def _setup_event_subscriptions(self) -> None:
        """Subscribe to download events from event bus."""
        self.event_bus.subscribe(DownloadEvent.PROGRESS, self._on_progress_event)
        self.event_bus.subscribe(DownloadEvent.COMPLETED, self._on_completed_event)
        self.event_bus.subscribe(DownloadEvent.FAILED, self._on_failed_event)

    # Event Handlers
    def _on_progress_event(
        self, download: Download, progress: float, speed: float
    ) -> None:
        """Handle progress event - update UI."""
        download_list = self.container.get("download_list")
        if download_list:
            try:
                download_list.update_item_progress(download, progress)
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error updating progress: {e}")

        status_bar = self.container.get("status_bar")
        if status_bar:
            status_bar.show_message(f"Downloading {download.name}: {progress:.1f}%")

    def _on_completed_event(self, download: Download) -> None:
        """Handle completion event - update UI."""
        self._refresh_ui_after_event(enable_buttons=True)
        self._update_status(f"Download completed: {download.name}")

    def _on_failed_event(self, download: Download, error: str) -> None:
        """Handle failure event - update UI and show error dialog.

        SINGLE PATH: Show error dialog via message queue ONLY.
        Don't duplicate with status bar error.
        """
        logger.error(f"[DOWNLOAD_COORDINATOR] Failed: {download.name} - {error}")

        # Refresh download list
        download_list = self.container.get("download_list")
        if download_list:
            try:
                download_list.refresh_items(download_list.get_downloads())
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

        # Enable action buttons
        action_buttons = self.container.get("action_buttons")
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
            return False

        try:
            self._auto_clear_completed_downloads()
            download.set_event_bus(self.event_bus)
            self._download_handler.add_download(download)

            download_list = self.container.get("download_list")
            if download_list:
                try:
                    download_list.add_download(download)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error adding to list: {e}")

            self._update_status(f"Download added: {download.name}")

            url_entry = self.container.get("url_entry")
            if url_entry:
                from src.utils.type_helpers import safe_clear

                safe_clear(url_entry)

            return True

        except Exception as e:
            logger.error(f"[DOWNLOAD_COORDINATOR] Failed to add download: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "Add Download Failed", f"Failed to add download: {str(e)}"
                )
            return False

    def remove_downloads(self, indices: List[int]) -> bool:
        """Remove downloads by indices - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] Download handler not available")
            return False

        if not indices:
            logger.warning("[DOWNLOAD_COORDINATOR] No indices provided for removal")
            return False

        try:
            logger.info(
                f"[DOWNLOAD_COORDINATOR] Removing downloads at indices: {indices}"
            )
            self._download_handler.remove_downloads(indices)
            self._refresh_ui_after_event(enable_buttons=True)
            self._update_status(f"Removed {len(indices)} item(s)")
            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to remove downloads: {e}", exc_info=True
            )
            if self.error_handler:
                self.error_handler.show_error(
                    "Remove Downloads Failed", f"Failed to remove downloads: {str(e)}"
                )
            return False

    def clear_downloads(self) -> bool:
        """Clear all downloads - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] Download handler not available")
            return False

        try:
            logger.info("[DOWNLOAD_COORDINATOR] Clearing all downloads")
            self._download_handler.clear_downloads()
            self._refresh_ui_after_event(enable_buttons=True)
            self._update_status("All downloads cleared")
            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to clear downloads: {e}", exc_info=True
            )
            if self.error_handler:
                self.error_handler.show_error(
                    "Clear Downloads Failed", f"Failed to clear downloads: {str(e)}"
                )
            return False

    def clear_completed_downloads(self) -> int:
        """Clear completed downloads - manual trigger."""
        download_list = self.container.get("download_list")
        if not download_list:
            return 0

        try:
            from src.utils.type_helpers import remove_completed_downloads

            count = remove_completed_downloads(download_list)

            if count == 0:
                self._update_status("No completed downloads to clear")
            else:
                self._update_status(f"Cleared {count} completed download(s)")

            return count
        except Exception as e:
            logger.error(f"[DOWNLOAD_COORDINATOR] Failed to clear completed: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "Clear Completed Failed",
                    f"Failed to clear completed downloads: {str(e)}",
                )
            return 0

    def _auto_clear_completed_downloads(self) -> int:
        """Auto-clear completed downloads (before adding new)."""
        download_list = self.container.get("download_list")
        if not download_list:
            return 0

        from src.utils.type_helpers import (
            has_completed_downloads,
            remove_completed_downloads,
        )

        if not has_completed_downloads(download_list):
            return 0

        return remove_completed_downloads(download_list)

    def start_downloads(self, download_dir: Optional[str] = None) -> bool:
        """Start all pending downloads - delegates to download_handler."""
        if not self._download_handler:
            return False

        download_list = self.container.get("download_list")
        if not download_list or not download_list.has_items():
            self._update_status("Please add items to download")
            return False

        downloads = self._download_handler.get_downloads()
        if not downloads:
            self._update_status("No downloads available")
            return False

        try:
            for download in downloads:
                download.status = DownloadStatus.DOWNLOADING
                download.progress = 0.0

            if download_list:
                try:
                    download_list.refresh_items(downloads)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

            action_buttons = self.container.get("action_buttons")
            if action_buttons:
                try:
                    action_buttons.set_enabled(False)
                except Exception as e:
                    logger.error(f"[DOWNLOAD_COORDINATOR] Error disabling buttons: {e}")

            self._update_status("Starting downloads...")

            if not download_dir:
                download_dir = self.container.get("downloads_folder") or "~/Downloads"

            self._download_handler.start_downloads(
                downloads=downloads,
                download_dir=download_dir,
                progress_callback=lambda download, progress: download.update_progress(
                    progress, 0
                ),
                completion_callback=None,
            )

            return True

        except Exception as e:
            logger.error(f"[DOWNLOAD_COORDINATOR] Failed to start downloads: {e}")
            if self.error_handler:
                self.error_handler.show_error(
                    "Start Downloads Failed", f"Failed to start downloads: {str(e)}"
                )

            action_buttons = self.container.get("action_buttons")
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
