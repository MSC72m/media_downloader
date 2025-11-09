"""Event handling interfaces following Interface Segregation Principle."""

from abc import ABC, abstractmethod
from typing import List, Callable, Any, Optional, Dict
from ..core.models import Download


class URLDetectionHandler(ABC):
    """Interface for URL detection handlers."""

    @abstractmethod
    def detect_url_type(self, url: str) -> Optional[str]:
        """Detect the type of URL."""
        pass

    @abstractmethod
    def handle_detected_url(self, url: str, context: Any) -> bool:
        """Handle a detected URL."""
        pass


class DownloadManagementHandler(ABC):
    """Interface for download management handlers."""

    @abstractmethod
    def add_download(self, download: Download) -> bool:
        """Add a download to the system."""
        pass

    @abstractmethod
    def remove_downloads(self, indices: List[int]) -> bool:
        """Remove downloads by indices."""
        pass

    @abstractmethod
    def clear_downloads(self) -> bool:
        """Clear all downloads."""
        pass

    @abstractmethod
    def start_downloads(self) -> bool:
        """Start all pending downloads."""
        pass


class UIUpdateHandler(ABC):
    """Interface for UI update handlers."""

    @abstractmethod
    def update_status(self, message: str, is_error: bool = False) -> None:
        """Update status bar message."""
        pass

    @abstractmethod
    def update_progress(self, download: Download, progress: float) -> None:
        """Update download progress."""
        pass

    @abstractmethod
    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        """Update button enabled/disabled states."""
        pass

    @abstractmethod
    def show_error(self, title: str, message: str) -> None:
        """Show error dialog."""
        pass


class AuthenticationHandler(ABC):
    """Interface for authentication handlers."""

    @abstractmethod
    def authenticate_instagram(self, parent_window: Any, callback: Callable[[bool], None]) -> None:
        """Handle Instagram authentication."""
        pass

    @abstractmethod
    def handle_cookie_detection(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection."""
        pass


class FileManagementHandler(ABC):
    """Interface for file management handlers."""

    @abstractmethod
    def show_file_manager(self) -> None:
        """Show file manager dialog."""
        pass

    @abstractmethod
    def browse_files(self, file_types: List[str]) -> Optional[str]:
        """Browse for files."""
        pass


class ConfigurationHandler(ABC):
    """Interface for configuration handlers."""

    @abstractmethod
    def get_download_directory(self) -> str:
        """Get download directory."""
        pass

    @abstractmethod
    def set_download_directory(self, directory: str) -> bool:
        """Set download directory."""
        pass

    @abstractmethod
    def save_configuration(self) -> bool:
        """Save current configuration."""
        pass


class NetworkStatusHandler(ABC):
    """Interface for network status handlers."""

    @abstractmethod
    def check_connectivity(self) -> bool:
        """Check internet connectivity."""
        pass

    @abstractmethod
    def check_service_status(self, services: List[str]) -> Dict[str, bool]:
        """Check status of specific services."""
        pass

    @abstractmethod
    def show_network_status(self) -> None:
        """Show network status dialog."""
        pass


class YouTubeSpecificHandler(ABC):
    """Interface for YouTube-specific functionality."""

    @abstractmethod
    def handle_youtube_download(self, url: str, name: str, options: dict) -> None:
        """Handle YouTube download completion."""
        pass

    @abstractmethod
    def show_youtube_dialog(self, url: str, cookie_path: Optional[str] = None, browser: Optional[str] = None) -> None:
        """Show YouTube download dialog."""
        pass
