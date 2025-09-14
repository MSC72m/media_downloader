"""Main application controller that orchestrates all business logic."""

import logging
from typing import Dict, Any, List, Callable
from ..abstractions import (
    IApplicationController,
    IDownloadHandler,
    IAuthenticationHandler,
    IServiceDetector,
    INetworkChecker,
    IUIEventHandler
)
from src.models import DownloadItem, ServiceType, UIState, DownloadOptions

logger = logging.getLogger(__name__)


class ApplicationController(IApplicationController):
    """Main controller that orchestrates all business logic handlers."""

    def __init__(
        self,
        download_handler: IDownloadHandler,
        auth_handler: IAuthenticationHandler,
        service_detector: IServiceDetector,
        network_checker: INetworkChecker,
        ui_event_handler: IUIEventHandler
    ):
        self._download_handler = download_handler
        self._auth_handler = auth_handler
        self._service_detector = service_detector
        self._network_checker = network_checker
        self._ui_event_handler = ui_event_handler

        self._ui_state = UIState()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize all handlers."""
        if self._initialized:
            return

        try:
            self._download_handler.initialize()
            self._auth_handler.initialize()
            self._service_detector.initialize()
            self._network_checker.initialize()
            self._ui_event_handler.initialize()

            self._initialized = True
            logger.info("Application controller initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize application controller: {e}")
            raise

    def cleanup(self) -> None:
        """Clean up all handlers."""
        try:
            self._download_handler.cleanup()
            self._auth_handler.cleanup()
            self._network_checker.cleanup()
            self._ui_event_handler.cleanup()

            self._initialized = False
            logger.info("Application controller cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_download_handler(self) -> IDownloadHandler:
        """Get the download handler."""
        return self._download_handler

    def get_auth_handler(self) -> IAuthenticationHandler:
        """Get the authentication handler."""
        return self._auth_handler

    def get_service_detector(self) -> IServiceDetector:
        """Get the service detector."""
        return self._service_detector

    def get_network_checker(self) -> INetworkChecker:
        """Get the network checker."""
        return self._network_checker

    def get_ui_event_handler(self) -> IUIEventHandler:
        """Get the UI event handler."""
        return self._ui_event_handler

    @property
    def ui_state(self) -> UIState:
        """Get the current UI state."""
        return self._ui_state

    def update_button_states(self, has_selection: bool, has_items: bool, is_downloading: bool = False):
        """Update button states in the UI state."""
        self._ui_state.update_button_states(has_selection, has_items, is_downloading)


class DefaultUIEventHandler(IUIEventHandler):
    """Default implementation of UI event handler."""

    def __init__(
        self,
        download_handler: IDownloadHandler,
        auth_handler: IAuthenticationHandler,
        service_detector: IServiceDetector,
        network_checker: INetworkChecker,
        app_controller: ApplicationController,
        message_callback: Callable[[str, str], None],
        error_callback: Callable[[str], None]
    ):
        self._download_handler = download_handler
        self._auth_handler = auth_handler
        self._service_detector = service_detector
        self._network_checker = network_checker
        self._app_controller = app_controller
        self._message_callback = message_callback
        self._error_callback = error_callback

    def initialize(self) -> None:
        """Initialize the handler."""
        pass

    def cleanup(self) -> None:
        """Clean up resources."""
        pass

    def handle_url_add(self, url: str, name: str) -> None:
        """Handle adding a new URL."""
        try:
            # Validate URL
            if not url.startswith('http'):
                raise ValueError("Invalid URL format. URL must start with http:// or https://")

            # Detect service type
            service_type = self._service_detector.detect_service(url)
            if not service_type:
                raise ValueError(
                    "Unsupported platform. Currently supported: YouTube, Twitter, Instagram, and Pinterest"
                )

            # Check service accessibility
            if not self._service_detector.is_service_accessible(service_type):
                raise ValueError(
                    f"Cannot connect to {service_type.value}. Please check your internet connection."
                )

            # Add download item
            item = DownloadItem(name=name, url=url)
            self._download_handler.add_item(item)

            # Update UI state
            self._app_controller.update_button_states(
                has_selection=bool(self._app_controller.ui_state.selected_indices),
                has_items=self._download_handler.has_items(),
                is_downloading=self._download_handler.has_active_downloads()
            )

            self._message_callback(f"Added: {name}", "success")

        except Exception as e:
            self._error_callback(f"Error adding URL: {str(e)}")

    def handle_remove_selected(self) -> None:
        """Handle removing selected items."""
        try:
            selected_indices = self._app_controller.ui_state.selected_indices
            if not selected_indices:
                self._message_callback("Please select items to remove", "info")
                return

            self._download_handler.remove_items(selected_indices)

            # Update UI state
            self._app_controller.ui_state.selected_indices = []
            self._app_controller.update_button_states(
                has_selection=False,
                has_items=self._download_handler.has_items(),
                is_downloading=self._download_handler.has_active_downloads()
            )

            self._message_callback("Selected items removed", "success")

        except Exception as e:
            self._error_callback(f"Error removing items: {str(e)}")

    def handle_clear_all(self) -> None:
        """Handle clearing all items."""
        try:
            if not self._download_handler.has_items():
                self._message_callback("No items to clear", "info")
                return

            self._download_handler.clear_items()

            # Update UI state
            self._app_controller.ui_state.selected_indices = []
            self._app_controller.update_button_states(
                has_selection=False,
                has_items=False,
                is_downloading=False
            )

            self._message_callback("All items cleared", "success")

        except Exception as e:
            self._error_callback(f"Error clearing items: {str(e)}")

    def handle_download_start(self) -> None:
        """Handle starting downloads."""
        try:
            if not self._download_handler.has_items():
                self._message_callback("Please add items to download", "info")
                return

            # Check for Instagram items that need authentication
            items = self._download_handler.get_items()
            has_instagram = any('instagram.com' in item.url for item in items)

            if has_instagram and not self._auth_handler.is_authenticated(ServiceType.INSTAGRAM):
                self._error_callback("Please log in to Instagram first")
                return

            # Check network connectivity
            problem_services = self._network_checker.get_problem_services()
            if problem_services:
                problem_list = ", ".join(problem_services)
                self._error_callback(f"Network connectivity issues with: {problem_list}")
                return

            # Start downloads
            def progress_callback(item: DownloadItem, progress: float):
                self._app_controller.update_button_states(
                    has_selection=bool(self._app_controller.ui_state.selected_indices),
                    has_items=True,
                    is_downloading=True
                )

            def completion_callback(success: bool, error: str = None):
                if success:
                    self._message_callback("Downloads completed", "success")
                else:
                    self._error_callback(f"Download error: {error}")

                self._app_controller.update_button_states(
                    has_selection=bool(self._app_controller.ui_state.selected_indices),
                    has_items=self._download_handler.has_items(),
                    is_downloading=self._download_handler.has_active_downloads()
                )

            self._download_handler.start_downloads(
                self._app_controller.ui_state.download_directory,
                progress_callback,
                completion_callback
            )

        except Exception as e:
            self._error_callback(f"Error starting downloads: {str(e)}")

    def handle_selection_change(self, selected_indices: List[int]) -> None:
        """Handle selection changes."""
        self._app_controller.ui_state.selected_indices = selected_indices
        self._app_controller.update_button_states(
            has_selection=bool(selected_indices),
            has_items=self._download_handler.has_items(),
            is_downloading=self._download_handler.has_active_downloads()
        )

    def handle_option_change(self, option: str, value: Any) -> None:
        """Handle option changes."""
        if option == 'quality':
            # Update download options with new quality
            options = self._download_handler.options
            options.quality = value
            self._download_handler.options = options
        elif option in ['playlist', 'audio_only']:
            # Update download options
            options = self._download_handler.options
            setattr(options, option, value)
            self._download_handler.options = options
