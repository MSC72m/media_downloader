"""Application orchestrator that coordinates all services and UI."""

import os
from src.utils.logger import get_logger
import customtkinter as ctk
from tkinter import messagebox
from typing import Any, Optional

from ..downloads.models import UIState
from ..events.queue import MessageQueue
from ..network.checker import check_internet_connection, check_all_services
from .container import ServiceContainer
from ..events.coordinator import EventCoordinator
from ..detection.link_detector import LinkDetector
from ..services.accessor import ServiceAccessor
from ...handlers.cookie_handler import CookieHandler
from ...handlers.auth_handler import AuthenticationHandler
from ...handlers.download_handler import DownloadHandler
from ...services.factory import ServiceFactory
from ...services.download import DownloadService
from ...services.youtube.cookie_detector import CookieManager, CookieDetector
from ...services.youtube.metadata_service import YouTubeMetadataService
from ...handlers.network_checker import NetworkChecker
from ...handlers.service_detector import ServiceDetector
from ...ui.dialogs.network_status_dialog import NetworkStatusDialog
from ..services.controller import ServiceController

logger = get_logger(__name__)


class ApplicationOrchestrator:
    """Orchestrates all application services and coordinates UI interactions."""

    def __init__(self, root_window: ctk.CTk):
        self.root = root_window
        self.ui_state = UIState()
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.message_queue = MessageQueue(root_window)

        # Initialize service container
        self.container = ServiceContainer()

        # Initialize event coordinator and link detection system
        self.event_coordinator = EventCoordinator(self.root, self.container)
        self.link_detector = LinkDetector()
        self.service_accessor = ServiceAccessor(self.container)

        # UI components (will be set by the main entrypoint)
        self.ui_components: dict[str, Any] = {}

        # Initialize services after event coordinator is created
        self._initialize_services()

        # Initialize event handling directly
        self._setup_event_handlers()

        logger.info("Application orchestrator initialized")

    def _initialize_services(self):
        """Initialize all application services using the container."""
        # Register singletons first
        self.container.register('ui_state', self.ui_state, singleton=True)
        self.container.register('message_queue', self.message_queue, singleton=True)
        self.container.register(
            'downloads_folder', self.downloads_folder, singleton=True
        )

        # Register service factories
        self.container.register_factory('cookie_detector', lambda: CookieDetector())
        self.container.register_factory(
            'auth_manager', lambda: self._create_auth_manager()
        )
        self.container.register_factory(
            'youtube_metadata', lambda: YouTubeMetadataService()
        )
        self.container.register_factory('network_checker', lambda: NetworkChecker())
        self.container.register_factory('service_detector', lambda: ServiceDetector())

        # Initialize core services
        cookie_manager = CookieManager()
        cookie_manager.initialize()

        service_factory = ServiceFactory(cookie_manager)
        download_service = DownloadService(service_factory)

        # Register core services
        self.container.register('cookie_manager', cookie_manager, singleton=True)
        self.container.register('service_factory', service_factory, singleton=True)
        self.container.register('download_service', download_service, singleton=True)

        # Initialize and register handlers using dependency injection
        auth_manager = self.container.get('auth_manager')
        self.container.register('auth_manager', auth_manager, singleton=True)

        cookie_handler = CookieHandler(cookie_manager)
        auth_handler = AuthenticationHandler(auth_manager)
        download_handler = DownloadHandler(self.container)
        network_checker = self.container.get('network_checker')
        service_detector = self.container.get('service_detector')

        # Initialize handlers
        auth_handler.initialize()
        network_checker.initialize()
        service_detector.initialize()
        download_handler.initialize()

        # Register handlers
        self.container.register('cookie_handler', cookie_handler, singleton=True)
        self.container.register('auth_handler', auth_handler, singleton=True)
        self.container.register(
            'download_handler', download_handler, singleton=True
        )
        self.container.register(
            'network_checker', network_checker, singleton=True
        )
        self.container.register(
            'service_detector', service_detector, singleton=True
        )

        # Create service controller
        self.container.register(
            'service_controller',
            ServiceController(
                download_service=download_service,
                cookie_manager=cookie_manager
            ),
            singleton=True
        )

        # Register orchestrator as event handler
        self.container.register('event_handler', self, singleton=True)

        # Register event coordinator
        self.container.register(
            'event_coordinator', self.event_coordinator, singleton=True
        )

        # Register UI components to event coordinator
        self.event_coordinator.download_list = self.ui_components.get('download_list')
        self.event_coordinator.status_bar = self.ui_components.get('status_bar')
        self.event_coordinator.action_buttons = self.ui_components.get('action_buttons')
        self.event_coordinator.url_entry = self.ui_components.get('url_entry')

        logger.info("All services registered in container")

    def _create_auth_manager(self):
        """Create a simple auth manager for now."""
        class SimpleAuthManager:
            def authenticate_instagram(self, parent_window, callback):
                # Simple implementation for now
                _ = parent_window  # Unused parameter
                callback(False)

            def cleanup(self):
                pass

        return SimpleAuthManager()

    def set_ui_components(self, **components):
        """Set UI component references."""
        logger.info("[ORCHESTRATOR] set_ui_components called with: %s", list(components.keys()))
        logger.info("[ORCHESTRATOR] components: %s", components)
        self.ui_components.update(components)

        # Update event coordinator with new UI components
        if hasattr(self, 'event_coordinator'):
            logger.info("[ORCHESTRATOR] Updating event coordinator with UI components")
            logger.info("[ORCHESTRATOR] event_coordinator before: %s", self.event_coordinator)

            self.event_coordinator.download_list = components.get('download_list')
            logger.info("[ORCHESTRATOR] Set download_list: %s", self.event_coordinator.download_list)

            self.event_coordinator.status_bar = components.get('status_bar')
            logger.info("[ORCHESTRATOR] Set status_bar: %s", self.event_coordinator.status_bar)

            self.event_coordinator.action_buttons = components.get('action_buttons')
            logger.info("[ORCHESTRATOR] Set action_buttons: %s", self.event_coordinator.action_buttons)

            self.event_coordinator.url_entry = components.get('url_entry')
            logger.info("[ORCHESTRATOR] Set url_entry: %s", self.event_coordinator.url_entry)

            # Also set up the container with UI components
            logger.info("[ORCHESTRATOR] Setting up container with UI components")
            self.container.register('download_list', components.get('download_list'))
            self.container.register('status_bar', components.get('status_bar'))
            self.container.register('action_buttons', components.get('action_buttons'))
            self.container.register('url_entry', components.get('url_entry'))

            logger.info("[ORCHESTRATOR] Container updated with UI components")

            # Refresh handlers after UI components are registered
            logger.info("[ORCHESTRATOR] Refreshing event coordinator handlers")
            self.event_coordinator.refresh_handlers()
            logger.info("[ORCHESTRATOR] Event coordinator handlers refreshed")
            return

        logger.warning(
            "[ORCHESTRATOR] event_coordinator not found, cannot update UI components"
        )

        logger.info("[ORCHESTRATOR] UI components registered successfully")

    def check_connectivity(self):
        """Check internet connectivity at startup."""
        if hasattr(self, 'event_coordinator'):
            self.event_coordinator.update_status(
                "Checking network connectivity..."
            )

        def check_worker():
            internet_connected, error_msg = check_internet_connection()
            service_results = check_all_services()
            problem_services = [
                service for service, (connected, _) in service_results.items()
                if not connected
            ]

            self.root.after(0, lambda: self._handle_connectivity_check(
                internet_connected, error_msg, problem_services
            ))

        import threading
        threading.Thread(target=check_worker, daemon=True).start()

    def _handle_connectivity_check(
        self, internet_connected: bool, error_msg: str, problem_services: list
    ):
        """Handle the results of the connectivity check."""
        if not internet_connected:
            messagebox.showwarning(
                "Network Connectivity Issue",
                f"There are network connectivity issues:\n\n{error_msg}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            if hasattr(self, 'event_coordinator'):
                self.event_coordinator.update_status(
                    "Network connectivity issues detected", is_error=True
                )
        elif problem_services:
            problem_list = ", ".join(problem_services)
            messagebox.showwarning(
                "Service Connection Issues",
                f"Cannot connect to the following services: {problem_list}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            if hasattr(self, 'event_coordinator'):
                self.event_coordinator.update_status(
                    f"Connection issues with: {problem_list}", is_error=True
                )
        else:
            if hasattr(self, 'event_coordinator'):
                self.event_coordinator.update_status("Ready - All services connected")

    def show_network_status(self):
        """Show network status dialog."""
        if hasattr(self, 'event_coordinator'):
            self.event_coordinator.show_network_status()
            return

        # Fallback for backward compatibility
        NetworkStatusDialog(self.root)

    def cleanup(self):
        """Clean up all services."""
        try:
            # Clean up services that need cleanup
            cookie_handler = self.container.get('cookie_handler')
            auth_handler = self.container.get('auth_handler')
            download_handler = self.container.get('download_handler')
            network_checker = self.container.get('network_checker')

            if cookie_handler:
                cookie_handler.cleanup()
            if auth_handler:
                auth_handler.cleanup()
            if download_handler:
                download_handler.cleanup()
            if network_checker:
                network_checker.cleanup()

            self.container.clear()
            logger.info("Application cleanup completed")
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e))

    def _setup_event_handlers(self):
        """Set up direct event handling methods."""
        logger.info("Event handlers initialized")

    def handle_add_url(self, url: str, name: Optional[str] = None):
        """Handle adding a new URL using the new detection system."""
        # Use the new link detection system
        _ = name  # Unused parameter
        self.link_detector.detect_and_handle(url, self.event_coordinator)

    def handle_remove(self):
        """Handle removing selected items."""
        download_list = self.ui_components.get('download_list')
        if not download_list:
            return

        selected_indices = download_list.get_selected_indices()
        self.event_coordinator.remove_downloads(selected_indices)

    def handle_clear(self):
        """Handle clearing all items."""
        self.event_coordinator.clear_downloads()

    def handle_download(self):
        """Handle starting downloads."""
        logger.info("[ORCHESTRATOR] handle_download called")
        logger.info("[ORCHESTRATOR] event_coordinator: %s", self.event_coordinator)
        try:
            self.event_coordinator.start_downloads()
            logger.info("[ORCHESTRATOR] event_coordinator.start_downloads() called successfully")
        except Exception as e:
            logger.exception("[ORCHESTRATOR] Error calling event_coordinator.start_downloads(): %s", e)

    def handle_selection_change(self, selected_indices: list):
        """Handle selection changes."""
        logger.info("[ORCHESTRATOR] handle_selection_change called with: %s", selected_indices)
        download_list = self.ui_components.get('download_list')
        logger.info("[ORCHESTRATOR] download_list: %s", download_list)
        has_items = download_list.has_items() if download_list else False
        logger.info("[ORCHESTRATOR] has_items: %s, has_selection: %s", has_items, bool(selected_indices))
        try:
            self.event_coordinator.update_button_states(bool(selected_indices), has_items)
            logger.info("[ORCHESTRATOR] update_button_states called successfully")
        except Exception as e:
            logger.exception("[ORCHESTRATOR] Error calling update_button_states: %s", e)

    
    def handle_instagram_login(self, parent_window=None):
        """Handle Instagram login."""
        self.event_coordinator.authenticate_instagram(parent_window)

    def handle_youtube_detected(self, url: str):
        """Handle YouTube URL detection using the new detection system."""
        # Use the new link detection system
        self.link_detector.detect_and_handle(url, self.event_coordinator)

    def handle_cookie_detected(self, browser_type: str, cookie_path: str):
        """Handle cookie detection."""
        self.event_coordinator.handle_cookie_detection(browser_type, cookie_path)

    def handle_cookie_manual_select(self):
        """Handle manual cookie selection."""
        cookie_path = self.event_coordinator.browse_files(['txt', 'cookies'])
        if cookie_path:
            self.event_coordinator.handle_cookie_detection("manual", cookie_path)

    def handle_manage_files(self):
        """Handle file management."""
        self.event_coordinator.show_file_manager()

    # Core service access methods
    def get_service(self, service_name: str):
        """Get a service from the container."""
        return self.service_accessor.get_service(service_name)

    def get_ui_component(self, component_name: str):
        """Get a UI component by name."""
        return self.service_accessor.get_ui_component(component_name, self.ui_components)

    def get_event_coordinator(self):
        """Get the event coordinator."""
        return self.service_accessor.event_coordinator