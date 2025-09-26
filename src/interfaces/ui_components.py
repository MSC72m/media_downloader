"""Abstract base classes for UI components."""

from abc import ABC, abstractmethod
from typing import List, Callable, Optional, Any
from src.core.models import UIState, Download, ServiceType


class IUIComponent(ABC):
    """Base interface for all UI components."""

    @abstractmethod
    def initialize(self, parent: Any) -> None:
        """Initialize the component with its parent."""
        pass

    @abstractmethod
    def update(self, state: Any) -> None:
        """Update the component with new state."""
        pass

    @abstractmethod
    def enable(self, enabled: bool = True) -> None:
        """Enable or disable the component."""
        pass

    @abstractmethod
    def show(self, visible: bool = True) -> None:
        """Show or hide the component."""
        pass


class IURLEntryComponent(IUIComponent):
    """Interface for URL entry components."""

    @abstractmethod
    def set_url_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for when URL is added."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear the URL entry."""
        pass


class IDownloadListComponent(IUIComponent):
    """Interface for download list components."""

    @abstractmethod
    def refresh_items(self, items: List[Download]) -> None:
        """Refresh the list with new items."""
        pass

    @abstractmethod
    def set_selection_callback(self, callback: Callable[[List[int]], None]) -> None:
        """Set callback for selection changes."""
        pass

    @abstractmethod
    def update_item_progress(self, item: Download, progress: float) -> None:
        """Update progress for a specific item."""
        pass


class IOptionsBarComponent(IUIComponent):
    """Interface for options bar components."""

    @abstractmethod
    def set_quality_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for quality changes."""
        pass

    @abstractmethod
    def set_option_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Set callback for option changes."""
        pass

    @abstractmethod
    def set_instagram_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for Instagram login."""
        pass

    @abstractmethod
    def set_instagram_status(self, status: Any) -> None:
        """Set Instagram authentication status."""
        pass


class IActionButtonsComponent(IUIComponent):
    """Interface for action button components."""

    @abstractmethod
    def set_remove_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for remove action."""
        pass

    @abstractmethod
    def set_clear_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for clear action."""
        pass

    @abstractmethod
    def set_download_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for download action."""
        pass

    @abstractmethod
    def set_manage_files_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for file management."""
        pass

    @abstractmethod
    def update_states(self, button_states: dict) -> None:
        """Update button states based on application state."""
        pass


class IStatusBarComponent(IUIComponent):
    """Interface for status bar components."""

    @abstractmethod
    def show_message(self, message: str, level: str = "info") -> None:
        """Show a message in the status bar."""
        pass

    @abstractmethod
    def show_error(self, message: str) -> None:
        """Show an error message."""
        pass

    @abstractmethod
    def show_warning(self, message: str) -> None:
        """Show a warning message."""
        pass


class IUIFactory(ABC):
    """Factory interface for creating UI components."""

    @abstractmethod
    def create_url_entry(self, parent: Any, callbacks: dict) -> IURLEntryComponent:
        """Create a URL entry component."""
        pass

    @abstractmethod
    def create_download_list(self, parent: Any, callbacks: dict) -> IDownloadListComponent:
        """Create a download list component."""
        pass

    @abstractmethod
    def create_options_bar(self, parent: Any, callbacks: dict) -> IOptionsBarComponent:
        """Create an options bar component."""
        pass

    @abstractmethod
    def create_action_buttons(self, parent: Any, callbacks: dict) -> IActionButtonsComponent:
        """Create action buttons component."""
        pass

    @abstractmethod
    def create_status_bar(self, parent: Any) -> IStatusBarComponent:
        """Create a status bar component."""
        pass


class IDialog(ABC):
    """Base interface for dialogs."""

    @abstractmethod
    def show(self) -> None:
        """Show the dialog."""
        pass

    @abstractmethod
    def hide(self) -> None:
        """Hide the dialog."""
        pass

    @abstractmethod
    def wait_window(self) -> Any:
        """Wait for the dialog to close."""
        pass


class INetworkStatusDialog(IDialog):
    """Interface for network status dialogs."""

    @abstractmethod
    def update_status(self, services_status: dict) -> None:
        """Update the network status display."""
        pass


class IFileManagerDialog(IDialog):
    """Interface for file manager dialogs."""

    @abstractmethod
    def set_directory_change_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for directory changes."""
        pass

    @abstractmethod
    def set_current_directory(self, directory: str) -> None:
        """Set the current directory."""
        pass


class IDialogFactory(ABC):
    """Factory interface for creating dialogs."""

    @abstractmethod
    def create_network_status_dialog(self, parent: Any) -> INetworkStatusDialog:
        """Create a network status dialog."""
        pass

    @abstractmethod
    def create_file_manager_dialog(
        self,
        parent: Any,
        current_directory: str,
        directory_callback: Callable[[str], None],
        status_callback: Callable[[str], None]
    ) -> IFileManagerDialog:
        """Create a file manager dialog."""
        pass