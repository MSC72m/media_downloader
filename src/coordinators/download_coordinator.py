"""Download Coordinator - Delegates all download operations to download_handler."""

from typing import Callable, List, Optional

from src.core.models import Download, DownloadStatus
from src.services.events.event_bus import DownloadEvent, DownloadEventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadCoordinator:
    """Coordinates download operations by delegating to download_handler."""

    def __init__(self, container, event_bus: DownloadEventBus, ui_state_manager):
        """Initialize with service container, event bus, and UI state manager."""
        self.container = container
        self.event_bus = event_bus
        self.ui_state = ui_state_manager
        self._download_handler = None

        # Subscribe to download events
        self._setup_event_subscriptions()

    def refresh_handlers(self):
        """Refresh handler references from container."""
        self._download_handler = self.container.get("download_handler")
        logger.info("[DOWNLOAD_COORDINATOR] Handlers refreshed")

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
        self.ui_state.update_progress(download, progress)

    def _on_completed_event(self, download: Download) -> None:
        """Handle completion event - update UI."""
        logger.info(f"[DOWNLOAD_COORDINATOR] Completed: {download.name}")
        self.ui_state.refresh_download_list()
        self.ui_state.enable_action_buttons()
        self.ui_state.update_status(f"Download completed: {download.name}")

    def _on_failed_event(self, download: Download, error: str) -> None:
        """Handle failure event - update UI."""
        logger.error(f"[DOWNLOAD_COORDINATOR] Failed: {download.name} - {error}")
        self.ui_state.refresh_download_list()
        self.ui_state.enable_action_buttons()
        self.ui_state.show_error(error or "Download failed")

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

            # Update UI
            self.ui_state.add_download_to_list(download)
            self.ui_state.update_status(f"Download added: {download.name}")
            self.ui_state.clear_url_entry()

            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to add download: {e}", exc_info=True
            )
            self.ui_state.show_error(f"Failed to add download: {str(e)}")
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

            # Update UI
            self.ui_state.refresh_download_list()
            self.ui_state.update_status("Selected items removed")

            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to remove downloads: {e}", exc_info=True
            )
            self.ui_state.show_error(f"Failed to remove downloads: {str(e)}")
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

            # Update UI
            self.ui_state.refresh_download_list()
            self.ui_state.update_status("All items cleared")

            return True

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to clear downloads: {e}", exc_info=True
            )
            self.ui_state.show_error(f"Failed to clear downloads: {str(e)}")
            return False

    def clear_completed_downloads(self) -> int:
        """Clear completed downloads - manual trigger."""
        try:
            count = self.ui_state.remove_completed_downloads()
            if count > 0:
                self.ui_state.update_status(f"Cleared {count} completed download(s)")
            else:
                self.ui_state.update_status("No completed downloads to clear")
            return count
        except Exception as e:
            logger.error(
                f"[DOWNLOAD_COORDINATOR] Failed to clear completed: {e}", exc_info=True
            )
            self.ui_state.show_error(f"Failed to clear completed downloads: {str(e)}")
            return 0

    def _auto_clear_completed_downloads(self) -> int:
        """Auto-clear completed downloads (before adding new)."""
        if not self.ui_state.has_completed_downloads():
            return 0

        count = self.ui_state.remove_completed_downloads()
        logger.info(f"[DOWNLOAD_COORDINATOR] Auto-cleared {count} completed downloads")
        return count

    def start_downloads(self, download_dir: Optional[str] = None) -> bool:
        """Start all pending downloads - delegates to download_handler."""
        if not self._download_handler:
            logger.error("[DOWNLOAD_COORDINATOR] download_handler not available")
            return False

        try:
            # Check if there are items to download
            if not self.ui_state.has_items():
                self.ui_state.update_status("Please add items to download")
                return False

            # Get downloads from download_handler (single source of truth)
            downloads = self._download_handler.get_downloads()
            if not downloads:
                self.ui_state.update_status("No downloads available")
                return False

            logger.info(f"[DOWNLOAD_COORDINATOR] Starting {len(downloads)} downloads")

            # Set initial status on all downloads
            for download in downloads:
                download.status = DownloadStatus.DOWNLOADING
                download.progress = 0.0

            # Refresh UI to show updated status
            self.ui_state.refresh_download_list(downloads)

            # Define progress callback
            def on_progress(download: Download, progress: float) -> None:
                """Progress callback - download updates itself via event bus."""
                download.update_progress(progress, 0)

            # Disable buttons during download
            self.ui_state.disable_action_buttons()
            self.ui_state.update_status("Starting downloads...")

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
            self.ui_state.show_error(f"Failed to start downloads: {str(e)}")
            self.ui_state.enable_action_buttons()
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
