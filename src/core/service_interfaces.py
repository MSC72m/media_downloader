"""Service interfaces for type-safe dependency injection."""

from typing import List, Optional, Callable, Any, Protocol

from src.core.models import Download


class IDownloadService(Protocol):
    """Interface for download services."""

    def add_download(self, download: Download) -> None:
        """Add a download item."""
        ...

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        ...

    def clear_downloads(self) -> None:
        """Clear all download items."""
        ...

    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        ...

    def has_downloads(self) -> bool:
        """Check if there are any downloads."""
        ...


class ICookieHandler(Protocol):
    """Interface for cookie handling."""

    def detect_cookies(self, callback: Callable[[str, str], None]) -> None:
        """Detect available cookies."""
        ...

    def validate_cookies(self, cookie_path: str) -> bool:
        """Validate cookie file."""
        ...


class IAutoCookieManager(Protocol):
    """Interface for automatic cookie management."""

    def initialize(self) -> Any:
        """Initialize cookie manager."""
        ...

    def is_ready(self) -> bool:
        """Check if cookies are ready."""
        ...

    def is_generating(self) -> bool:
        """Check if cookies are being generated."""
        ...

    def get_cookies(self) -> Optional[str]:
        """Get cookie file path."""
        ...


class IYouTubeMetadataService(Protocol):
    """Interface for YouTube metadata service."""

    def fetch_metadata(self, url: str) -> Optional[Any]:
        """Fetch metadata for a YouTube URL."""
        ...

    def get_available_qualities(self, url: str) -> List[str]:
        """Get available video qualities for a YouTube URL."""
        ...

    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube URL."""
        ...


class INetworkChecker(Protocol):
    """Interface for network checking."""

    def check_connectivity(self) -> tuple[bool, str]:
        """Check network connectivity."""
        ...

    def is_connected(self) -> bool:
        """Check if connected to internet."""
        ...


class IServiceFactory(Protocol):
    """Interface for service factory."""

    def detect_service_type(self, url: str) -> str:
        """Detect service type for URL."""
        ...

    def create_downloader(self, url: str) -> Any:
        """Create appropriate downloader for URL."""
        ...


class IMessageQueue(Protocol):
    """Interface for message queue."""

    def add_message(self, message: Any) -> None:
        """Add a message to the queue."""
        ...

    def send_message(self, message: dict) -> None:
        """Send a message."""
        ...


class IErrorHandler(Protocol):
    """Interface for error handling."""

    def show_error(self, title: str, message: str) -> None:
        """Show error message."""
        ...

    def log_error(self, error: Exception, context: str = "") -> None:
        """Log error with context."""
        ...