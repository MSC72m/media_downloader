"""Service controller that delegates to the download handler."""

from src.utils.logger import get_logger
import threading

logger = get_logger(__name__)


class ServiceController:
    """Simple controller that delegates downloads to the download handler."""

    def __init__(self, download_service, cookie_manager):
        self.download_service = download_service
        self.cookie_manager = cookie_manager
        self._active_downloads = 0
        self._lock = threading.Lock()

    def start_downloads(self, downloads, download_dir, progress_callback=None, completion_callback=None) -> None:
        """Start downloads by delegating to the DownloadService with early returns."""
        logger.info(f"[SERVICE_CONTROLLER] Starting {len(downloads)} downloads")

        if not self.download_service:
            logger.error("[SERVICE_CONTROLLER] download_service is not set")
            if completion_callback:
                completion_callback(False, "Download service not available")
            return None

        try:
            # DownloadService manages its own repository; adapt by registering items there
            # If download_service exposes a direct start with provided items, prefer that
            if hasattr(self.download_service, 'start_downloads'):
                self.download_service.start_downloads(
                    download_dir=download_dir,
                    progress_callback=progress_callback,
                    completion_callback=completion_callback
                )
                return None

            logger.error("[SERVICE_CONTROLLER] download_service.start_downloads not available")
            if completion_callback:
                completion_callback(False, "Download service cannot start downloads")
        except Exception as e:
            logger.error(f"[SERVICE_CONTROLLER] Error starting downloads: {e}", exc_info=True)
            if completion_callback:
                completion_callback(False, str(e))
        return None

    def has_active_downloads(self):
        """Check if there are active downloads."""
        # This could be implemented by tracking active downloads
        # For now, return False as the download handler manages this
        return False

    def _safe_decode_bytes(self, byte_data: bytes) -> str:
        """Safely decode bytes with multiple fallback encodings."""
        if not byte_data:
            return ""

        # Try UTF-8 first (most common)
        try:
            return byte_data.decode('utf-8')
        except UnicodeDecodeError:
            pass

        # Try latin-1 (handles all byte values)
        try:
            return byte_data.decode('latin-1')
        except UnicodeDecodeError:
            pass

        # Final fallback: replace problematic characters
        try:
            return byte_data.decode('utf-8', errors='replace')
        except Exception:
            # Last resort: use repr to show raw bytes
            return repr(byte_data)
