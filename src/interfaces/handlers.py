"""Abstract base classes for the application's business logic layer."""

from abc import ABC, abstractmethod
from typing import List, Callable, Optional, Any
from src.core.models import Download, DownloadOptions, ServiceType, UIState


class IHandler(ABC):
    """Base interface for all handlers with lifecycle management."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the handler and its dependencies."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources and stop any ongoing operations."""
        pass


class IDownloadHandler(IHandler):
    """Lightweight interface for download operations - delegates to existing DownloadManager."""

    @abstractmethod
    def add_item(self, item: Download) -> None:
        """Add a download item to the queue."""
        pass

    @abstractmethod
    def remove_items(self, indices: List[int]) -> None:
        """Remove items at the specified indices."""
        pass

    @abstractmethod
    def clear_items(self) -> None:
        """Clear all download items."""
        pass

    @abstractmethod
    def get_items(self) -> List[Download]:
        """Get all download items."""
        pass

    @abstractmethod
    def has_items(self) -> bool:
        """Check if there are any items."""
        pass

    @abstractmethod
    def start_downloads(
        self,
        download_dir: str,
        progress_callback: Callable[[Download, float], None],
        completion_callback: Callable[[bool, Optional[str]], None]
    ) -> None:
        """Start downloading all pending items."""
        pass

    @abstractmethod
    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        pass

    @property
    @abstractmethod
    def options(self) -> DownloadOptions:
        """Get download options."""
        pass

    @options.setter
    @abstractmethod
    def options(self, value: DownloadOptions) -> None:
        """Set download options."""
        pass


class IAuthenticationHandler(IHandler):
    """Lightweight interface for authentication operations - delegates to existing AuthManager."""

    @abstractmethod
    def authenticate_instagram(
        self,
        parent_window: Any,
        callback: Callable[[bool], None]
    ) -> None:
        """Authenticate with Instagram."""
        pass

    @abstractmethod
    def is_authenticated(self, service: ServiceType) -> bool:
        """Check if authenticated with a service."""
        pass


class IServiceDetector(IHandler):
    """Interface for detecting service types from URLs - consolidates duplicated logic."""

    @abstractmethod
    def detect_service(self, url: str) -> Optional[ServiceType]:
        """Detect service type from URL."""
        pass

    @abstractmethod
    def is_service_accessible(self, service: ServiceType) -> bool:
        """Check if a service is accessible."""
        pass


class INetworkChecker(IHandler):
    """Interface for network connectivity checks - uses existing utility functions."""

    @abstractmethod
    def check_internet_connection(self) -> tuple[bool, str]:
        """Check general internet connectivity."""
        pass

    @abstractmethod
    def check_service_connection(self, service: ServiceType) -> tuple[bool, str]:
        """Check connection to a specific service."""
        pass

    @abstractmethod
    def get_problem_services(self) -> List[str]:
        """Get list of services with connection issues."""
        pass


class IUIEventHandler(IHandler):
    """Interface for handling UI events - coordinates between handlers and UI."""

    @abstractmethod
    def handle_url_add(self, url: str, name: str) -> None:
        """Handle adding a new URL."""
        pass

    @abstractmethod
    def handle_remove_selected(self) -> None:
        """Handle removing selected items."""
        pass

    @abstractmethod
    def handle_clear_all(self) -> None:
        """Handle clearing all items."""
        pass

    @abstractmethod
    def handle_download_start(self) -> None:
        """Handle starting downloads."""
        pass

    @abstractmethod
    def handle_selection_change(self, selected_indices: List[int]) -> None:
        """Handle selection changes."""
        pass

    @abstractmethod
    def handle_option_change(self, option: str, value: Any) -> None:
        """Handle option changes."""
        pass

    @abstractmethod
    def handle_cookie_detection(self, url: str) -> bool:
        """Handle cookie detection for a URL."""
        pass


class IApplicationController(IHandler):
    """Main controller that orchestrates all handlers and manages application state."""

    @abstractmethod
    def get_download_handler(self) -> IDownloadHandler:
        """Get the download handler."""
        pass

    @abstractmethod
    def get_auth_handler(self) -> IAuthenticationHandler:
        """Get the authentication handler."""
        pass

    @abstractmethod
    def get_service_detector(self) -> IServiceDetector:
        """Get the service detector."""
        pass

    @abstractmethod
    def get_network_checker(self) -> INetworkChecker:
        """Get the network checker."""
        pass

    @abstractmethod
    def get_ui_event_handler(self) -> IUIEventHandler:
        """Get the UI event handler."""
        pass

    @property
    @abstractmethod
    def ui_state(self) -> UIState:
        """Get the current UI state."""
        pass

    @abstractmethod
    def update_button_states(self, has_selection: bool, has_items: bool, is_downloading: bool = False) -> None:
        """Update button states in the UI state."""
        pass
