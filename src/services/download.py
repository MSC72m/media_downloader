"""Download service for business logic."""

import threading
from src.utils.logger import get_logger
from typing import List, Callable, Optional
from ..core.models import Download, DownloadStatus
from .factory import ServiceFactory
from .downloads.repository import DownloadRepository, OptionsRepository

logger = get_logger(__name__)


class DownloadService:
    """Service for handling download business logic."""

    def __init__(self, service_factory: ServiceFactory):
        self._factory = service_factory
        self._repository = DownloadRepository()
        self._options_repository = OptionsRepository()
        self._active_downloads = 0
        self._lock = threading.Lock()
        self._progress_callbacks: List[Callable] = []

    def add_download(self, url: str, name: str) -> bool:
        """
        Add a new download.

        Args:
            url: URL to download
            name: Name for the download

        Returns:
            True if successful, False otherwise
        """
        try:
            service_type = self._factory.detect_service_type(url)
            if not service_type:
                logger.error(f"Unsupported URL: {url}")
                return False

            download = Download(
                name=name,
                url=url,
                service_type=service_type
            )

            self._repository.add(download)
            logger.info(f"Added download: {name} from {url}")
            return True

        except Exception as e:
            logger.error(f"Error adding download: {e}")
            return False

    def remove_downloads(self, indices: List[int]) -> bool:
        """
        Remove downloads by indices.

        Args:
            indices: List of indices to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            self._repository.remove(indices)
            logger.info(f"Removed downloads at indices: {indices}")
            return True
        except Exception as e:
            logger.error(f"Error removing downloads: {e}")
            return False

    def clear_downloads(self) -> bool:
        """
        Clear all downloads.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._repository.clear()
            logger.info("Cleared all downloads")
            return True
        except Exception as e:
            logger.error(f"Error clearing downloads: {e}")
            return False

    def start_downloads(
        self,
        download_dir: str,
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> bool:
        """
        Start all pending downloads.

        Args:
            download_dir: Directory to save downloads
            progress_callback: Callback for progress updates
            completion_callback: Callback for completion notification

        Returns:
            True if downloads started, False otherwise
        """
        try:
            pending_downloads = self._repository.get_pending()
            if not pending_downloads:
                logger.info("No pending downloads")
                if completion_callback:
                    completion_callback(True, "No downloads to process")
                return True

            # Start downloads in separate threads
            for download in pending_downloads:
                threading.Thread(
                    target=self._download_worker,
                    args=(download, download_dir, progress_callback, completion_callback),
                    daemon=True
                ).start()

            return True

        except Exception as e:
            logger.error(f"Error starting downloads: {e}")
            if completion_callback:
                completion_callback(False, str(e))
            return False

    def _download_worker(
        self,
        download: Download,
        download_dir: str,
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> None:
        """Worker thread for handling a single download."""
        try:
            with self._lock:
                self._active_downloads += 1

            # Update status to downloading
            self._repository.update_download(
                self._repository.get_all().index(download),
                status=DownloadStatus.DOWNLOADING
            )

            # Get appropriate downloader
            downloader = self._factory.get_downloader(download.url)
            if not downloader:
                raise Exception(f"No downloader available for {download.service_type}")

            # Create save path
            save_path = f"{download_dir}/{download.name}"

            # Progress wrapper
            def progress_wrapper(progress: float, speed: float = 0):
                download.update_progress(progress, speed)
                self._repository.update_download(
                    self._repository.get_all().index(download),
                    progress=progress,
                    speed=speed
                )
                if progress_callback:
                    progress_callback(download, progress)

            # Perform download
            success = downloader.download(download.url, save_path, progress_wrapper)

            # Update status
            if success:
                self._repository.update_download(
                    self._repository.get_all().index(download),
                    status=DownloadStatus.COMPLETED
                )
                logger.info(f"Download completed: {download.name}")
            else:
                download.mark_failed("Download failed")
                self._repository.update_download(
                    self._repository.get_all().index(download),
                    status=DownloadStatus.FAILED,
                    error_message=download.error_message
                )
                logger.error(f"Download failed: {download.name}")

        except Exception as e:
            logger.error(f"Error in download worker for {download.name}: {e}")
            download.mark_failed(str(e))
            self._repository.update_download(
                self._repository.get_all().index(download),
                status=DownloadStatus.FAILED,
                error_message=download.error_message
            )

        finally:
            with self._lock:
                self._active_downloads -= 1

            # Check if all downloads are complete
            if self._active_downloads == 0:
                remaining = len(self._repository.get_pending())
                if remaining == 0 and completion_callback:
                    completion_callback(True, None)

    def get_downloads(self) -> List[Download]:
        """Get all downloads."""
        return self._repository.get_all()

    def has_downloads(self) -> bool:
        """Check if there are any downloads."""
        return self._repository.has_items()

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        with self._lock:
            return self._active_downloads > 0

    def get_download_options(self) -> dict:
        """Get download options."""
        return self._options_repository.get_all()

    def set_download_option(self, key: str, value) -> None:
        """Set a download option."""
        self._options_repository.set(key, value)

    def add_progress_observer(self, callback: Callable) -> None:
        """Add a progress observer."""
        self._progress_callbacks.append(callback)