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