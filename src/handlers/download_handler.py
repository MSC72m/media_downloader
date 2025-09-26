"""Concrete implementation of download handler."""

import logging
from typing import List, Callable, Optional
from ..interfaces import IDownloadHandler, IHandler
from src.models import DownloadItem, DownloadOptions
from src.controllers.download_manager import DownloadManager

logger = logging.getLogger(__name__)


class DownloadHandler(IDownloadHandler):
    """Lightweight handler that delegates to existing DownloadManager."""

    def __init__(self, download_manager: DownloadManager = None):
        self._download_manager = download_manager or DownloadManager()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the download handler."""
        if self._initialized:
            return
        self._initialized = True

    def cleanup(self) -> None:
        """Clean up resources."""
        self._download_manager.cleanup()
        self._initialized = False

    def add_item(self, item: DownloadItem) -> None:
        """Delegate to existing DownloadManager."""
        self._download_manager.add_item(item)

    def remove_items(self, indices: List[int]) -> None:
        """Delegate to existing DownloadManager."""
        self._download_manager.remove_items(indices)

    def clear_items(self) -> None:
        """Delegate to existing DownloadManager."""
        self._download_manager.clear_items()

    def get_items(self) -> List[DownloadItem]:
        """Delegate to existing DownloadManager."""
        return self._download_manager.items

    def has_items(self) -> bool:
        """Delegate to existing DownloadManager."""
        return self._download_manager.has_items()

    def start_downloads(
        self,
        download_dir: str,
        progress_callback: Callable[[DownloadItem, float], None],
        completion_callback: Callable[[bool, Optional[str]], None]
    ) -> None:
        """Delegate to existing DownloadManager."""
        self._download_manager.start_downloads(download_dir, progress_callback, completion_callback)

    def has_active_downloads(self) -> bool:
        """Delegate to existing DownloadManager."""
        return self._download_manager.has_active_downloads()

    @property
    def options(self) -> DownloadOptions:
        """Delegate to existing DownloadManager."""
        return self._download_manager.options

    @options.setter
    def options(self, value: DownloadOptions) -> None:
        """Delegate to existing DownloadManager."""
        # Map properties to existing manager
        self._download_manager.quality = value.quality.value
        self._download_manager.set_option('playlist', value.playlist)
        self._download_manager.set_option('audio_only', value.audio_only)