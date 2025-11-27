"""Service interfaces for dependency injection."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Any

from src.core.models import Download, DownloadOptions


class IDownloadService(ABC):
    """Interface for download services."""

    @abstractmethod
    def add_download(self, download: Download) -> None:
        """Add a download item."""
        pass

    @abstractmethod
    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        pass

    @abstractmethod
    def clear_downloads(self) -> None:
        """Clear all download items."""
        pass

    @abstractmethod
    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        pass

    @abstractmethod
    def start_download(self, download: Download, options: DownloadOptions) -> None:
        """Start a download."""
        pass

    @abstractmethod
    def pause_download(self, download: Download) -> None:
        """Pause a download."""
        pass

    @abstractmethod
    def cancel_download(self, download: Download) -> None:
        """Cancel a download."""
        pass


class IDownloadHandler(ABC):
    """Interface for download handling."""

    @abstractmethod
    def process_url(self, url: str, options: Optional[dict] = None) -> bool:
        """Process a URL for download."""
        pass

    @abstractmethod
    def handle_download_error(self, error: Exception) -> None:
        """Handle download errors."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if handler is available."""
        pass


class ICookieHandler(ABC):
    """Interface for cookie handling."""

    @abstractmethod
    def detect_cookies(self, callback: Callable[[str, str], None]) -> None:
        """Detect available cookies."""
        pass

    @abstractmethod
    def validate_cookies(self, cookie_path: str) -> bool:
        """Validate cookie file."""
        pass


class IMetadataService(ABC):
    """Interface for metadata services."""

    @abstractmethod
    def get_metadata(self, url: str) -> dict:
        """Get metadata for URL."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if service is available."""
        pass


class INetworkChecker(ABC):
    """Interface for network checking."""

    @abstractmethod
    def check_connectivity(self) -> tuple[bool, str]:
        """Check network connectivity."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to internet."""
        pass


class IFileService(ABC):
    """Interface for file operations."""

    @abstractmethod
    def ensure_directory(self, path: str) -> bool:
        """Ensure directory exists."""
        pass

    @abstractmethod
    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        """Get unique filename in directory."""
        pass

    @abstractmethod
    def clean_filename(self, filename: str) -> str:
        """Clean filename for filesystem."""
        pass


class IMessageQueue(ABC):
    """Interface for message queue."""

    @abstractmethod
    def send_message(self, message: dict) -> None:
        """Send a message."""
        pass

    @abstractmethod
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register message handler."""
        pass


class IErrorHandler(ABC):
    """Interface for error handling."""

    @abstractmethod
    def show_error(self, title: str, message: str) -> None:
        """Show error message."""
        pass

    @abstractmethod
    def show_warning(self, title: str, message: str) -> None:
        """Show warning message."""
        pass

    @abstractmethod
    def show_info(self, title: str, message: str) -> None:
        """Show info message."""
        pass

    @abstractmethod
    def set_message_queue(self, message_queue: IMessageQueue) -> None:
        """Set message queue instance."""
        pass


class IServiceFactory(ABC):
    """Interface for service factory."""

    @abstractmethod
    def create_downloader(self, url: str) -> Any:
        """Create appropriate downloader for URL."""
        pass

    @abstractmethod
    def detect_service_type(self, url: str) -> str:
        """Detect service type for URL."""
        pass


class IAutoCookieManager(ABC):
    """Interface for automatic cookie management."""

    @abstractmethod
    def initialize(self) -> Any:
        """Initialize cookie manager."""
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if cookies are ready."""
        pass

    @abstractmethod
    def is_generating(self) -> bool:
        """Check if cookies are being generated."""
        pass

    @abstractmethod
    def get_cookies(self) -> Optional[str]:
        """Get cookie file path."""
        pass


class IUIState(ABC):
    """Interface for UI state management."""

    @abstractmethod
    def get_current_url(self) -> str:
        """Get current URL."""
        pass

    @abstractmethod
    def set_current_url(self, url: str) -> None:
        """Set current URL."""
        pass

    @abstractmethod
    def is_busy(self) -> bool:
        """Check if UI is busy."""
        pass

    @abstractmethod
    def set_busy(self, busy: bool) -> None:
        """Set UI busy state."""
        pass


# ============================================================================
# DOWNLOADER BASE CLASSES AND EXCEPTIONS
# ============================================================================

class BaseDownloader(ABC):
    """Base class for all media downloaders."""

    @abstractmethod
    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Download media from a URL.

        Args:
            url: URL to download from
            save_path: Path to save the downloaded media
            progress_callback: Callback for progress updates (progress percentage, speed)

        Returns:
            True if download was successful, False otherwise
        """
        pass

    def _ensure_directory_exists(self, file_path: str) -> None:
        """
        Ensure the directory for the given file path exists.

        Args:
            file_path: Full path to the file
        """
        import os
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _get_save_directory(self, save_path: str) -> str:
        """
        Extract directory path from save path.

        Args:
            save_path: Full path or directory path

        Returns:
            Directory path
        """
        import os
        return os.path.dirname(save_path) if os.path.dirname(save_path) else "."


class NetworkError(Exception):
    """Exception raised for network-related errors."""

    def __init__(self, message: str, is_temporary: bool = False):
        """
        Initialize network error.

        Args:
            message: Error message
            is_temporary: Whether the error is likely temporary (e.g., rate limiting)
        """
        self.message = message
        self.is_temporary = is_temporary
        super().__init__(self.message)


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""

    def __init__(self, message: str, service: str = ""):
        """
        Initialize authentication error.

        Args:
            message: Error message
            service: Service name where auth failed
        """
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)


class ServiceError(Exception):
    """Exception raised for service-related errors."""

    def __init__(self, message: str, service: str = ""):
        """
        Initialize service error.

        Args:
            message: Error message
            service: Service name where error occurred
        """
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)