"""Concrete implementation of download handler."""

import logging
from typing import List, Callable, Optional
from src.core.models import Download, DownloadOptions
from src.core.container import ServiceContainer

logger = logging.getLogger(__name__)


class DownloadHandler:
    """Download handler using service container."""

    def __init__(self, container: ServiceContainer):
        self.container = container
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the download handler."""
        if self._initialized:
            return
        self._initialized = True

    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False

    def add_download(self, download: Download) -> None:
        """Add a download item."""
        download_service = self.container.get('download_service')
        if download_service:
            download_service.add_download(download)

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        download_service = self.container.get('download_service')
        if download_service:
            download_service.remove_downloads(indices)

    def clear_downloads(self) -> None:
        """Clear all download items."""
        download_service = self.container.get('download_service')
        if download_service:
            download_service.clear_downloads()

    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        download_service = self.container.get('download_service')
        if download_service:
            return download_service.get_downloads()
        return []

    def has_items(self) -> bool:
        """Check if there are any download items."""
        downloads = self.get_downloads()
        return len(downloads) > 0

    def start_downloads(
        self,
        downloads: List[Download],
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> None:
        """Start downloads."""
        service_controller = self.container.get('service_controller')
        if service_controller:
            service_controller.start_downloads(downloads, progress_callback, completion_callback)

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        service_controller = self.container.get('service_controller')
        if service_controller:
            return service_controller.has_active_downloads()
        return False

    def get_options(self) -> DownloadOptions:
        """Get current download options."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            return DownloadOptions(
                save_directory=getattr(ui_state, 'download_directory', '~/Downloads')
            )
        return DownloadOptions()

    def set_options(self, options: DownloadOptions) -> None:
        """Set download options."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            ui_state.download_directory = options.save_directory