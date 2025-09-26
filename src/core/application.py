"""Application orchestrator that coordinates all services and UI."""

import os
import logging
from typing import Optional
import customtkinter as ctk
from tkinter import messagebox

from .models import UIState
from .message_queue import MessageQueue
from .network import check_internet_connection, check_all_services
from .container import ServiceContainer
from ..handlers.application_controller import ApplicationController

logger = logging.getLogger(__name__)


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
        self._initialize_services()

        # Initialize application controller
        self.app_controller = ApplicationController(self)
        self.app_controller.initialize()

        # UI components (will be set by the main entrypoint)
        self.ui_components = {}

        logger.info("Application orchestrator initialized")

    def _initialize_services(self):
        """Initialize all application services using the container."""
        # Register singletons first
        self.container.register('ui_state', self.ui_state, singleton=True)
        self.container.register('message_queue', self.message_queue, singleton=True)
        self.container.register('downloads_folder', self.downloads_folder, singleton=True)

        # Register service factories
        self.container.register_factory('cookie_detector', lambda: CookieDetector())
        self.container.register_factory('auth_manager', lambda: AuthenticationManager())
        self.container.register_factory('network_checker', lambda: NetworkChecker())
        self.container.register_factory('service_detector', lambda: ServiceDetector())

        # Initialize core services
        cookie_detector = self.container.get('cookie_detector')
        cookie_manager = CookieManager(cookie_detector)
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

        self.cookie_handler = CookieHandler(cookie_manager)
        self.auth_handler = AuthenticationHandler(auth_manager)
        self.download_handler = DownloadHandler(self.container)
        self.network_checker = self.container.get('network_checker')
        self.service_detector = self.container.get('service_detector')

        # Initialize handlers
        self.auth_handler.initialize()
        self.network_checker.initialize()
        self.service_detector.initialize()
        self.download_handler.initialize()

        # Register handlers
        self.container.register('cookie_handler', self.cookie_handler, singleton=True)
        self.container.register('auth_handler', self.auth_handler, singleton=True)
        self.container.register('download_handler', self.download_handler, singleton=True)
        self.container.register('network_checker', self.network_checker, singleton=True)
        self.container.register('service_detector', self.service_detector, singleton=True)

        # Initialize and register main controller
        service_controller = ServiceController(
            download_service=download_service,
            service_factory=service_factory,
            cookie_manager=cookie_manager
        )
        self.container.register('service_controller', service_controller, singleton=True)

        # Register application controller
        self.container.register('app_controller', self.app_controller, singleton=True)

        logger.info("All services registered in container")

    def set_ui_components(self, **components):
        """Set UI component references."""
        self.ui_components.update(components)
        logger.debug("UI components registered")

    def handle(self, event_name: str, *args, **kwargs):
        """Handle an event through the application controller."""
        return self.app_controller.handle_event(event_name, *args, **kwargs)

    def get_service(self, service_name: str):
        """Get a service from the container."""
        return self.container.get(service_name)

    def check_connectivity(self):
        """Check internet connectivity at startup."""
        status_bar = self.ui_components.get('status_bar')
        if status_bar:
            status_bar.show_message("Checking network connectivity...")

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

    def _handle_connectivity_check(self, internet_connected: bool, error_msg: str, problem_services: list):
        """Handle the results of the connectivity check."""
        status_bar = self.ui_components.get('status_bar')

        if not internet_connected:
            messagebox.showwarning(
                "Network Connectivity Issue",
                f"There are network connectivity issues:\n\n{error_msg}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            if status_bar:
                status_bar.show_warning("Network connectivity issues detected")
        elif problem_services:
            problem_list = ", ".join(problem_services)
            messagebox.showwarning(
                "Service Connection Issues",
                f"Cannot connect to the following services: {problem_list}\n\n"
                "You can view detailed network status from Tools > Network Status."
            )
            if status_bar:
                status_bar.show_warning(f"Connection issues with: {problem_list}")
        else:
            if status_bar:
                status_bar.show_message("Ready - All services connected")

    def show_network_status(self):
        """Show network status dialog."""
        from ..ui.dialogs.network_status_dialog import NetworkStatusDialog
        NetworkStatusDialog(self.root)

    def cleanup(self):
        """Clean up all services."""
        try:
            # Clean up services that need cleanup
            cookie_handler = self.container.get('cookie_handler')
            auth_handler = self.container.get('auth_handler')
            download_handler = self.container.get('download_handler')
            network_checker = self.container.get('network_checker')
            app_controller = self.container.get('app_controller')

            if cookie_handler:
                cookie_handler.cleanup()
            if auth_handler:
                auth_handler.cleanup()
            if download_handler:
                download_handler.cleanup()
            if network_checker:
                network_checker.cleanup()
            if app_controller:
                app_controller.cleanup()

            self.container.clear()
            logger.info("Application cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    # Convenience properties for common services
    @property
    def service_controller(self):
        """Get the service controller."""
        return self.container.get('service_controller')

    @property
    def cookie_handler(self):
        """Get the cookie handler."""
        return self.container.get('cookie_handler')

    @property
    def auth_handler(self):
        """Get the auth handler."""
        return self.container.get('auth_handler')

    @property
    def network_checker(self):
        """Get the network checker."""
        return self.container.get('network_checker')

    @property
    def service_detector(self):
        """Get the service detector."""
        return self.container.get('service_detector')

    # Convenience properties for UI components
    @property
    def url_entry(self):
        """Get the URL entry component."""
        return self.ui_components.get('url_entry')

    @property
    def options_bar(self):
        """Get the options bar component."""
        return self.ui_components.get('options_bar')

    @property
    def download_list(self):
        """Get the download list component."""
        return self.ui_components.get('download_list')

    @property
    def action_buttons(self):
        """Get the action buttons component."""
        return self.ui_components.get('action_buttons')

    @property
    def status_bar(self):
        """Get the status bar component."""
        return self.ui_components.get('status_bar')

    @property
    def cookie_selector(self):
        """Get the cookie selector component."""
        return self.ui_components.get('cookie_selector')