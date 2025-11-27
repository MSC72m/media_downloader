"""Download Coordinator - Delegates all download operations to download_handler."""

from typing import List, Optional, Callable, Any

from src.core.interfaces import (
    IDownloadHandler,
    IDownloadService,
    IErrorHandler,
    IMessageQueue,
)
from src.core.models import Download, DownloadStatus
from src.services.events.event_bus import DownloadEvent, DownloadEventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadCoordinator:
    """Coordinates download operations by delegating to download_handler.

    This coordinator focuses on business logic and delegates UI updates
    to callbacks provided by the UI layer.
    """

    def __init__(
        self,
        event_bus: DownloadEventBus,
        download_handler: IDownloadHandler,
        error_handler: IErrorHandler,
        download_service: IDownloadService,
        message_queue: Optional[IMessageQueue] = None,
        ui_callbacks: Optional[dict[str, Callable]] = None,
    ):
        """Initialize with injected dependencies and optional UI callbacks."""
        self.event_bus = event_bus
        self.download_handler = download_handler
        self.error_handler = error_handler
        self.download_service = download_service
        self.message_queue = message_queue
        self.ui_callbacks = ui_callbacks or {}

        # Subscribe to download events
        self._setup_event_subscriptions()

    def set_message_queue(self, message_queue: IMessageQueue) -> None:
        """Set message queue instance - used for late binding."""
        self.message_queue = message_queue
        logger.info("[DOWNLOAD_COORDINATOR] Message queue updated")

    def set_ui_callbacks(self, callbacks: dict[str, Callable]) -> None:
        """Set UI callbacks."""
        self.ui_callbacks.update(callbacks)
        logger.info(f"[DOWNLOAD_COORDINATOR] UI callbacks updated: {list(callbacks.keys())}")

    def _get_ui_callback(self, callback_name: str) -> Optional[Callable]:
        """Get a UI callback if available."""
        return self.ui_callbacks.get(callback_name)

    def _update_status(self, message: str, is_error: bool = False):
        """Update status via callback or message queue."""
        # Try UI callback first
        status_callback = self._get_ui_callback("update_status")
        if status_callback:
            try:
                status_callback(message, is_error)
                return
            except Exception as e:
                logger.warning(f"[DOWNLOAD_COORDINATOR] UI status callback failed: {e}")

        # Fallback to message queue
        if self.message_queue:
            try:
                from src.services.events.queue import Message
                from src.core.enums.message_level import MessageLevel

                level = MessageLevel.ERROR if is_error else MessageLevel.INFO
                self.message_queue.add_message(Message(text=message, level=level))
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Message queue failed: {e}")
        else:
            logger.info(f"[DOWNLOAD_COORDINATOR] Status: {message}")

    def _refresh_ui_after_event(self, enable_buttons: bool = True) -> None:
        """Refresh UI components after download event via callbacks."""
        refresh_callback = self._get_ui_callback("refresh_download_list")
        if refresh_callback:
            try:
                # Get downloads from the service (source of truth)
                downloads = self.download_service.get_downloads()
                refresh_callback(downloads)
                logger.debug(
                    f"[DOWNLOAD_COORDINATOR] Refreshed UI with {len(downloads)} downloads"
                )
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error refreshing list: {e}")

        if enable_buttons:
            buttons_callback = self._get_ui_callback("set_action_buttons_enabled")
            if buttons_callback:
                try:
                    buttons_callback(True)
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
        progress_callback = self._get_ui_callback("update_download_progress")
        if progress_callback:
            try:
                progress_callback(download, progress)
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error updating progress: {e}")

        self._update_status(f"Downloading {download.name}: {progress:.1f}%")

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

        # Show error message via message queue
        if self.message_queue:
            try:
                from src.services.events.queue import Message
                from src.core.enums.message_level import MessageLevel

                self.message_queue.add_message(
                    Message(
                        text=f"Download failed: {download.name}\n{error}",
                        level=MessageLevel.ERROR,
                        title="Download Error",
                    )
                )
            except Exception as msg_error:
                logger.error(
                    f"[DOWNLOAD_COORDINATOR] Failed to show error message: {msg_error}"
                )

        # Always refresh UI after failure
        self._refresh_ui_after_event(enable_buttons=True)

    # Public API Methods
    def add_download(self, download: Download) -> None:
        """Add a download via the download handler."""
        if self.download_handler:
            try:
                self.download_handler.add_download(download)
                logger.info(f"[DOWNLOAD_COORDINATOR] Added download: {download.name}")
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error adding download: {e}")
                self._update_status(f"Failed to add download: {e}", is_error=True)
        else:
            logger.error("[DOWNLOAD_COORDINATOR] Download handler not available")

    def start_downloads(
        self,
        downloads: List[Download],
        download_dir: str = "~/Downloads",
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> None:
        """Start downloads via the download handler."""
        if self.download_handler:
            try:
                self.download_handler.start_downloads(
                    downloads, download_dir, progress_callback, completion_callback
                )
                logger.info(f"[DOWNLOAD_COORDINATOR] Starting {len(downloads)} downloads")
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error starting downloads: {e}")
                self._update_status(f"Failed to start downloads: {e}", is_error=True)
        else:
            logger.error("[DOWNLOAD_COORDINATOR] Download handler not available")

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove downloads via the download handler."""
        if self.download_handler:
            try:
                self.download_handler.remove_downloads(indices)
                logger.info(f"[DOWNLOAD_COORDINATOR] Removed downloads at indices: {indices}")
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error removing downloads: {e}")
                self._update_status(f"Failed to remove downloads: {e}", is_error=True)
        else:
            logger.error("[DOWNLOAD_COORDINATOR] Download handler not available")

    def clear_downloads(self) -> None:
        """Clear all downloads via the download handler."""
        if self.download_handler:
            try:
                self.download_handler.clear_downloads()
                logger.info("[DOWNLOAD_COORDINATOR] Cleared all downloads")
            except Exception as e:
                logger.error(f"[DOWNLOAD_COORDINATOR] Error clearing downloads: {e}")
                self._update_status(f"Failed to clear downloads: {e}", is_error=True)
        else:
            logger.error("[DOWNLOAD_COORDINATOR] Download handler not available")

    def get_downloads(self) -> List[Download]:
        """Get all downloads via the download service."""
        try:
            return self.download_service.get_downloads() or []
        except Exception as e:
            logger.error(f"[DOWNLOAD_COORDINATOR] Error getting downloads: {e}")
            return []

    def has_items(self) -> bool:
        """Check if there are any downloads."""
        try:
            return len(self.get_downloads()) > 0
        except Exception:
            return False

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        try:
            downloads = self.get_downloads()
            return any(
                d.status in [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]
                for d in downloads
            )
        except Exception:
            return False

    def cancel_all_downloads(self) -> None:
        """Cancel all active downloads."""
        try:
            downloads = self.get_downloads()
            for download in downloads:
                if download.status in [DownloadStatus.PENDING, DownloadStatus.DOWNLOADING]:
                    self.download_handler.cancel_download(download)
            logger.info("[DOWNLOAD_COORDINATOR] Cancelled all active downloads")
        except Exception as e:
            logger.error(f"[DOWNLOAD_COORDINATOR] Error cancelling downloads: {e}")

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("[DOWNLOAD_COORDINATOR] Cleaning up")
        # The event bus and other services are managed by the orchestrator