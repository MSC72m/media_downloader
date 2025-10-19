"""Service controller that delegates to the download handler."""

import logging
import threading

logger = logging.getLogger(__name__)


class ServiceController:
    """Simple controller that delegates downloads to the download handler."""

    def __init__(self, download_service, cookie_manager):
        self.download_service = download_service
        self.cookie_manager = cookie_manager
        self._active_downloads = 0
        self._lock = threading.Lock()

    def start_downloads(self, downloads, download_dir, progress_callback=None, completion_callback=None):
        """Start downloads by delegating to the download handler."""
        logger.info(f"[SERVICE_CONTROLLER] Starting {len(downloads)} downloads")
        
        # Get download handler from the service
        if download_handler := (
            getattr(self.download_service, 'download_handler', None) or
            (getattr(self.download_service, 'container', None) and 
             self.download_service.container.get('download_handler'))
        ):
            download_handler.start_downloads(
                downloads, 
                download_dir, 
                progress_callback, 
                completion_callback
            )
        else:
            logger.error("[SERVICE_CONTROLLER] No download handler available")
            if completion_callback:
                completion_callback(False, "No download handler available")

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
