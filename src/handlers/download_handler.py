"""Concrete implementation of download handler."""

from src.utils.logger import get_logger
from typing import List, Callable, Optional
from src.core.models import Download, DownloadOptions
from src.core.application.container import ServiceContainer

logger = get_logger(__name__)


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
        if download_service := self.container.get('download_service'):
            download_service.add_download(download)

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        if download_service := self.container.get('download_service'):
            download_service.remove_downloads(indices)

    def clear_downloads(self) -> None:
        """Clear all download items."""
        if download_service := self.container.get('download_service'):
            download_service.clear_downloads()

    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        if download_service := self.container.get('download_service'):
            if downloads := download_service.get_downloads():
                return downloads
        return []

    def has_items(self) -> bool:
        """Check if there are any download items."""
        downloads = self.get_downloads()
        return len(downloads) > 0

    def start_downloads(
        self,
        downloads: List[Download],
        download_dir: str = "~/Downloads",
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> None:
        """Start downloads by delegating to appropriate service handlers."""
        logger.info(f"[DOWNLOAD_HANDLER] Starting {len(downloads)} downloads")
        
        for download in downloads:
            # Start each download in a separate thread
            import threading
            thread = threading.Thread(
                target=self._download_worker,
                args=(download, download_dir, progress_callback, completion_callback),
                daemon=True
            )
            thread.start()

    def _download_worker(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Worker function to handle a single download by delegating to service factory with early returns."""
        logger.info(f"[DOWNLOAD_HANDLER] download_worker called for: {download.name}")
        try:
            service_factory = self.container.get('service_factory')
            if not service_factory:
                msg = "Service factory not available"
                logger.error(f"[DOWNLOAD_HANDLER] {msg}")
                if completion_callback:
                    completion_callback(False, msg)
                return

            downloader = service_factory.get_downloader(download.url)
            if not downloader:
                msg = f"No downloader available for URL: {download.url}"
                logger.error(f"[DOWNLOAD_HANDLER] {msg}")
                if completion_callback:
                    completion_callback(False, msg)
                return

            # Create output dir and sanitized filename via FileService
            from pathlib import Path
            file_service = service_factory.get_file_service()
            target_dir = Path(download_dir).expanduser()
            target_dir.mkdir(parents=True, exist_ok=True)
            base_name = file_service.sanitize_filename(download.name or "download")
            ext = ".mp4"
            if getattr(download, 'audio_only', False):
                ext = ".mp3"
            output_path = str(target_dir / f"{base_name}{ext}")

            def progress_wrapper(progress, speed):
                if progress_callback:
                    progress_callback(download, int(progress))

            success = downloader.download(
                url=download.url,
                save_path=output_path,
                progress_callback=progress_wrapper
            )

            if not success:
                msg = f"Failed to download: {download.name}"
                logger.error(f"[DOWNLOAD_HANDLER] {msg}")
                if completion_callback:
                    completion_callback(False, msg)
                return

            logger.info(f"[DOWNLOAD_HANDLER] Successfully downloaded: {download.name}")
            if completion_callback:
                completion_callback(True, f"Downloaded: {download.name}")
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logger.error(f"[DOWNLOAD_HANDLER] Download error for {download.name}: {e}")
            if completion_callback:
                completion_callback(False, error_msg)

    def _handle_youtube_download(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Deprecated: unified through factory in _download_worker."""
        self._download_worker(download, download_dir, progress_callback, completion_callback)

    def _handle_twitter_download(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Deprecated: unified through factory in _download_worker."""
        self._download_worker(download, download_dir, progress_callback, completion_callback)

    def _handle_instagram_download(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Deprecated: unified through factory in _download_worker."""
        self._download_worker(download, download_dir, progress_callback, completion_callback)

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        if service_controller := self.container.get('service_controller'):
            if result := service_controller.has_active_downloads():
                return result
        return False

    def get_options(self) -> DownloadOptions:
        """Get current download options."""
        if ui_state := self.container.get('ui_state'):
            return DownloadOptions(
                save_directory=getattr(ui_state, 'download_directory', '~/Downloads')
            )
        return DownloadOptions()

    def set_options(self, options: DownloadOptions) -> None:
        """Set download options."""
        if ui_state := self.container.get('ui_state'):
            ui_state.download_directory = options.save_directory