"""Simplified Application Orchestrator - Thin initialization layer."""

import os
from typing import Any

import customtkinter as ctk

from src.coordinators import EventCoordinator
from src.handlers import (
    AuthenticationHandler,
    CookieHandler,
    DownloadHandler,
    NetworkChecker,
    ServiceDetector,
)
from src.services.detection.link_detector import LinkDetector
from src.services.downloads import DownloadService, ServiceFactory
from src.services.events.queue import MessageQueue
from src.services.file import FileService
from src.services.network.checker import check_all_services, check_internet_connection
from src.services.youtube.cookie_detector import CookieDetector, CookieManager
from src.services.youtube.metadata_service import YouTubeMetadataService
from src.utils.logger import get_logger
from src.utils.type_helpers import safe_cleanup

from ..models import UIState
from .container import ServiceContainer

logger = get_logger(__name__)


class ApplicationOrchestrator:
    """Simplified orchestrator - initializes services and coordinates via event coordinator.

    Responsibilities:
    1. Initialize service container
    2. Register all services and handlers
    3. Create event coordinator
    4. Provide simple API for UI

    Does NOT:
    - Contain business logic
    - Duplicate handler logic
    - Manage UI directly
    """

    def __init__(self, root_window: ctk.CTk):
        """Initialize orchestrator with root window."""
        self.root = root_window

        # Initialize container and core state
        self.container = ServiceContainer()
        self.ui_state = UIState()
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)

        # Initialize message queue
        self.message_queue = MessageQueue(root_window)

        # Register core services
        self._register_core_services()

        # Initialize handlers
        self._initialize_handlers()

        # Create event coordinator (uses our new coordinator)
        self.event_coordinator = EventCoordinator(root_window, self.container)
        self.container.register(
            "event_coordinator", self.event_coordinator, singleton=True
        )

        # Initialize link detector
        self.link_detector = LinkDetector()

        # Register link handlers after coordinator is created
        self._register_link_handlers()

        # UI components (set by main.py)
        self.ui_components: dict[str, Any] = {}

        logger.info("[ORCHESTRATOR] Initialization complete")

    def _register_core_services(self) -> None:
        """Register core services in container."""
        logger.info("[ORCHESTRATOR] Registering core services")

        # Register singletons
        self.container.register("ui_state", self.ui_state, singleton=True)
        self.container.register("message_queue", self.message_queue, singleton=True)
        self.container.register(
            "downloads_folder", self.downloads_folder, singleton=True
        )

        # Register service factories
        self.container.register_factory("cookie_detector", lambda: CookieDetector())
        self.container.register_factory(
            "youtube_metadata", lambda: YouTubeMetadataService()
        )
        self.container.register_factory("network_checker", lambda: NetworkChecker())
        self.container.register_factory("service_detector", lambda: ServiceDetector())
        self.container.register_factory("file_service", lambda: FileService())

        # Initialize cookie manager
        cookie_manager = CookieManager()
        cookie_manager.initialize()
        self.container.register("cookie_manager", cookie_manager, singleton=True)

        # Initialize service factory and download service
        service_factory = ServiceFactory(cookie_manager)
        download_service = DownloadService(service_factory)

        self.container.register("service_factory", service_factory, singleton=True)
        self.container.register("download_service", download_service, singleton=True)

        logger.info("[ORCHESTRATOR] Core services registered")

    def _initialize_handlers(self) -> None:
        """Initialize and register all handlers."""
        logger.info("[ORCHESTRATOR] Initializing handlers")

        # Create handlers
        cookie_manager = self.container.get("cookie_manager")
        cookie_handler = CookieHandler(cookie_manager)

        auth_handler = AuthenticationHandler(self._create_simple_auth_manager())
        auth_handler.initialize()

        download_handler = DownloadHandler(self.container)
        download_handler.initialize()

        network_checker = NetworkChecker()
        network_checker.initialize()

        service_detector = ServiceDetector()
        service_detector.initialize()

        # Register handlers in container
        self.container.register("cookie_handler", cookie_handler, singleton=True)
        self.container.register("auth_handler", auth_handler, singleton=True)
        self.container.register("download_handler", download_handler, singleton=True)
        self.container.register("network_checker", network_checker, singleton=True)
        self.container.register("service_detector", service_detector, singleton=True)

        logger.info("[ORCHESTRATOR] Handlers initialized and registered")

    def _create_simple_auth_manager(self):
        """Create a simple auth manager (placeholder for future implementation)."""

        class SimpleAuthManager:
            def authenticate_instagram(self, parent_window, callback):
                callback(False)

            def cleanup(self):
                pass

        return SimpleAuthManager()

    def _register_link_handlers(self) -> None:
        """Register link handlers for URL detection."""
        try:
            from src.handlers import _register_link_handlers

            handlers = _register_link_handlers()
            logger.info(f"[ORCHESTRATOR] Registered {len(handlers)} link handlers")
            for handler in handlers:
                logger.info(f"[ORCHESTRATOR] - {handler.__name__}")
        except Exception as e:
            logger.error(
                f"[ORCHESTRATOR] Failed to register link handlers: {e}", exc_info=True
            )

    def set_ui_components(self, **components) -> None:
        """Set UI component references."""
        logger.info(f"[ORCHESTRATOR] Setting UI components: {list(components.keys())}")

        self.ui_components.update(components)

        # Register UI components in container
        for name, component in components.items():
            self.container.register(name, component)

        # Refresh event coordinator handlers (so it picks up UI components)
        self.event_coordinator.refresh_handlers()

        logger.info("[ORCHESTRATOR] UI components registered")

    # Convenience methods for UI
    def check_connectivity(self) -> None:
        """Check network connectivity at startup."""
        self.event_coordinator.update_status("Checking network connectivity...")

        def check_worker():
            """Worker thread for connectivity check."""
            internet_connected, error_msg = check_internet_connection()
            service_results = check_all_services()
            problem_services = [
                service
                for service, (connected, _) in service_results.items()
                if not connected
            ]

            self.root.after(
                0,
                lambda: self._handle_connectivity_check(
                    internet_connected, error_msg, problem_services
                ),
            )

        import threading

        threading.Thread(target=check_worker, daemon=True).start()

    def _handle_connectivity_check(
        self, internet_connected: bool, error_msg: str, problem_services: list
    ) -> None:
        """Handle connectivity check results."""
        from tkinter import messagebox

        if not internet_connected:
            messagebox.showwarning(
                "Network Connectivity Issue",
                f"There are network connectivity issues:\n\n{error_msg}\n\n"
                "You can view detailed network status from Tools > Network Status.",
            )
            self.event_coordinator.update_status(
                "Network connectivity issues detected", is_error=True
            )
        elif problem_services:
            problem_list = ", ".join(problem_services)
            messagebox.showwarning(
                "Service Connection Issues",
                f"Cannot connect to the following services: {problem_list}\n\n"
                "You can view detailed network status from Tools > Network Status.",
            )
            self.event_coordinator.update_status(
                f"Connection issues with: {problem_list}", is_error=True
            )
        else:
            self.event_coordinator.update_status("Ready - All services connected")

    def show_network_status(self) -> None:
        """Show network status dialog."""
        self.event_coordinator.show_network_status()

    def handle_cookie_detected(self, browser_type: str, cookie_path: str) -> None:
        """Handle cookie detection callback from UI."""
        self.event_coordinator.cookie_detected(browser_type, cookie_path)

    def handle_cookie_manual_select(self) -> None:
        """Handle manual cookie selection callback from UI."""
        cookie_path = self.event_coordinator.browse_files(["txt", "cookies"])
        if cookie_path:
            self.event_coordinator.cookie_detected("manual", cookie_path)

    def get_service(self, service_name: str):
        """Get a service from the container."""
        return self.container.get(service_name)

    def cleanup(self) -> None:
        """Clean up all services."""
        try:
            logger.info("[ORCHESTRATOR] Cleaning up services")

            # Clean up handlers using type-safe helper
            for handler_name in [
                "cookie_handler",
                "auth_handler",
                "download_handler",
                "network_checker",
            ]:
                handler = self.container.get(handler_name)
                if handler:
                    safe_cleanup(handler)

            # Clear container
            self.container.clear()

            logger.info("[ORCHESTRATOR] Cleanup complete")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error during cleanup: {e}", exc_info=True)
