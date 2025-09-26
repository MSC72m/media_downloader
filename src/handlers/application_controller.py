"""Main application controller that orchestrates all business logic."""

import logging
from typing import Dict, Any, List, Callable
from src.core.models import Download, ServiceType, UIState, DownloadOptions
from src.core.container import ServiceContainer

logger = logging.getLogger(__name__)


class ApplicationController:
    """Main controller that orchestrates all business logic handlers."""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.container = orchestrator.container
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the application controller."""
        if self._initialized:
            return
        self._initialized = True
        logger.info("Application controller initialized")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False
        logger.info("Application controller cleaned up")

    def handle_event(self, event_name: str, *args, **kwargs):
        """Handle UI events through the appropriate handler."""
        try:
            if event_name == 'add_url':
                return self._handle_add_url(*args, **kwargs)
            elif event_name == 'remove_selected':
                return self._handle_remove_selected()
            elif event_name == 'clear_all':
                return self._handle_clear_all()
            elif event_name == 'download_start':
                return self._handle_download_start()
            elif event_name == 'selection_change':
                return self._handle_selection_change(*args, **kwargs)
            elif event_name == 'quality_change':
                return self._handle_quality_change(*args, **kwargs)
            elif event_name == 'instagram_login':
                return self._handle_instagram_login(*args, **kwargs)
            elif event_name == 'youtube_detected':
                return self._handle_youtube_detected(*args, **kwargs)
            elif event_name == 'cookie_detected':
                return self._handle_cookie_detected(*args, **kwargs)
            elif event_name == 'cookie_manual_select':
                return self._handle_cookie_manual_select(*args, **kwargs)
            elif event_name == 'manage_files':
                return self._handle_manage_files()
            else:
                logger.warning(f"Unknown event: {event_name}")
                return None
        except Exception as e:
            logger.error(f"Error handling event {event_name}: {e}")
            status_bar = self.orchestrator.status_bar
            if status_bar:
                status_bar.show_error(f"Error: {str(e)}")

    def _handle_add_url(self, url: str, name: str = None):
        """Handle adding a new URL."""
        from src.core.models import Download

        # Validate URL
        if not url.startswith('http'):
            raise ValueError("Invalid URL format. URL must start with http:// or https://")

        # Detect service type
        service_detector = self.container.get('service_detector')
        service_type = service_detector.detect_service(url)
        if not service_type:
            raise ValueError("Unsupported platform")

        # Check service accessibility
        if not service_detector.is_service_accessible(service_type):
            raise ValueError(f"Cannot connect to {service_type.value}")

        # Create download item
        if not name:
            name = f"Media from {service_type.value}"

        download = Download(name=name, url=url, service_type=service_type)

        # Add to download list
        download_list = self.orchestrator.download_list
        if download_list:
            download_list.add_download(download)

        status_bar = self.orchestrator.status_bar
        if status_bar:
            status_bar.show_message(f"Added: {name}")

    def _handle_remove_selected(self):
        """Handle removing selected items."""
        download_list = self.orchestrator.download_list
        if not download_list:
            return

        selected_indices = download_list.get_selected_indices()
        if not selected_indices:
            status_bar = self.orchestrator.status_bar
            if status_bar:
                status_bar.show_message("Please select items to remove")
            return

        download_list.remove_downloads(selected_indices)

        status_bar = self.orchestrator.status_bar
        if status_bar:
            status_bar.show_message("Selected items removed")

    def _handle_clear_all(self):
        """Handle clearing all items."""
        download_list = self.orchestrator.download_list
        if not download_list:
            return

        download_list.clear_downloads()

        status_bar = self.orchestrator.status_bar
        if status_bar:
            status_bar.show_message("All items cleared")

    def _handle_download_start(self):
        """Handle starting downloads."""
        download_list = self.orchestrator.download_list
        if not download_list or not download_list.has_items():
            status_bar = self.orchestrator.status_bar
            if status_bar:
                status_bar.show_message("Please add items to download")
            return

        # Get service controller and start downloads
        service_controller = self.container.get('service_controller')
        if service_controller:
            downloads = download_list.get_downloads()
            service_controller.start_downloads(downloads)

    def _handle_selection_change(self, selected_indices: list):
        """Handle selection changes."""
        action_buttons = self.orchestrator.action_buttons
        if action_buttons:
            has_selection = bool(selected_indices)
            action_buttons.update_remove_button_state(has_selection)

    def _handle_quality_change(self, quality: str):
        """Handle quality changes."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            ui_state.quality = quality

    def _handle_instagram_login(self, parent_window=None):
        """Handle Instagram login."""
        auth_handler = self.container.get('auth_handler')
        if auth_handler:
            auth_handler.authenticate_instagram(parent_window, lambda success: None)

    def _handle_youtube_detected(self, url: str):
        """Handle YouTube URL detection."""
        cookie_handler = self.container.get('cookie_handler')
        cookie_selector = self.orchestrator.cookie_selector

        if cookie_handler and cookie_selector:
            should_show = cookie_handler.should_show_cookie_option(url)
            cookie_selector.set_visible(should_show)

    def _handle_cookie_detected(self, browser_type: str, cookie_path: str):
        """Handle cookie detection."""
        cookie_handler = self.container.get('cookie_handler')
        if cookie_handler:
            success = cookie_handler.set_cookie_file(cookie_path)
            status_bar = self.orchestrator.status_bar
            if status_bar:
                if success:
                    status_bar.show_message(f"Cookies loaded from {browser_type}")
                else:
                    status_bar.show_error("Failed to load cookies")

    def _handle_cookie_manual_select(self):
        """Handle manual cookie selection."""
        from src.ui.dialogs.file_manager_dialog import FileManagerDialog
        file_dialog = FileManagerDialog(self.orchestrator.root)
        cookie_path = file_dialog.select_file()

        if cookie_path:
            cookie_handler = self.container.get('cookie_handler')
            if cookie_handler:
                success = cookie_handler.set_cookie_file(cookie_path)
                status_bar = self.orchestrator.status_bar
                if status_bar:
                    if success:
                        status_bar.show_message("Cookie file loaded successfully")
                    else:
                        status_bar.show_error("Failed to load cookie file")

    def _handle_manage_files(self):
        """Handle file management."""
        from src.ui.dialogs.file_manager_dialog import FileManagerDialog
        FileManagerDialog(self.orchestrator.root)
