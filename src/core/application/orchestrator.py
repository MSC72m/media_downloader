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
        """Create Instagram auth manager with proper login dialog."""

        class InstagramAuthManager:
            """Manages Instagram authentication."""

            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
                self._is_authenticated = False

            def authenticate_instagram(self, parent_window, callback):
                """Show Instagram login dialog and authenticate."""
                try:
                    from src.services.instagram.downloader import InstagramDownloader
                    from src.ui.dialogs.login_dialog import LoginDialog

                    # Create and show login dialog
                    dialog = LoginDialog(parent_window)
                    dialog.wait_window()

                    # Check if user provided credentials
                    if not dialog.username or not dialog.password:
                        logger.info("[AUTH_MANAGER] Instagram login cancelled")
                        # Just call callback - platform_dialog_coordinator will handle state reset
                        callback(False)
                        return

                    # Store credentials for use in thread
                    username = dialog.username
                    password = dialog.password

                    # Capture references for the nested function
                    orchestrator = self.orchestrator
                    container = self.orchestrator.container
                    auth_manager = self

                    # Attempt authentication in background thread
                    def auth_worker():
                        success = False
                        error_message = None

                        try:
                            logger.info("[AUTH_MANAGER] Starting authentication worker")
                            downloader = InstagramDownloader()
                            success = downloader.authenticate(username, password)
                            logger.info(
                                f"[AUTH_MANAGER] Authentication completed with success={success}"
                            )

                        except Exception as e:
                            logger.error(
                                f"[AUTH_MANAGER] Authentication error: {e}",
                                exc_info=True,
                            )
                            error_message = str(e)
                            success = False

                        # Always update on main thread, regardless of success or failure
                        def update_main_thread():
                            try:
                                logger.info(
                                    f"[AUTH_MANAGER] Calling callback with success={success}, error={error_message}"
                                )

                                # Just call callback with error message
                                # platform_dialog_coordinator will handle ALL UI updates
                                callback(success, error_message)

                            except Exception as update_error:
                                logger.error(
                                    f"[AUTH_MANAGER] Error calling callback: {update_error}",
                                    exc_info=True,
                                )
                                # Fallback: call callback with failure
                                callback(False, str(update_error))

                        try:
                            if parent_window and hasattr(parent_window, "after"):
                                parent_window.after(0, update_main_thread)
                                logger.info(
                                    "[AUTH_MANAGER] Scheduled main thread update"
                                )
                            else:
                                logger.warning(
                                    "[AUTH_MANAGER] No parent_window or after method, calling directly"
                                )
                                update_main_thread()
                        except Exception as schedule_error:
                            logger.error(
                                f"[AUTH_MANAGER] Error scheduling main thread update: {schedule_error}",
                                exc_info=True,
                            )
                            # Just call callback with failure - no UI updates here
                            callback(False, str(schedule_error))

                    import threading

                    threading.Thread(target=auth_worker, daemon=True).start()

                except Exception as e:
                    logger.error(
                        f"[AUTH_MANAGER] Error showing login dialog: {e}", exc_info=True
                    )
                    # Just call callback with failure - platform_dialog_coordinator handles UI
                    callback(False, f"Failed to show login dialog: {str(e)}")

            def _handle_auth_result(self, success: bool, callback):
                """Handle authentication result - NO UI UPDATES HERE.

                Platform dialog coordinator is responsible for ALL UI updates.
                """
                self._is_authenticated = success
                logger.info(f"[AUTH_MANAGER] Authentication result: {success}")
                # Callback already called in update_main_thread - don't call again

            @property
            def is_authenticated(self):
                return self._is_authenticated

            def cleanup(self):
                pass

        return InstagramAuthManager(self)

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
        """Check network connectivity at startup - asynchronous to prevent UI freeze."""
        logger.info("[ORCHESTRATOR] Starting connectivity check")

        # Ensure event coordinator and UI components are ready
        if not self.event_coordinator:
            logger.error("[ORCHESTRATOR] Event coordinator not initialized")
            return

        self.event_coordinator.update_status("Checking network connectivity...")
        logger.info(
            "[ORCHESTRATOR] Status updated to 'Checking network connectivity...'"
        )

        # Run connectivity check in background thread to prevent UI freeze
        def connectivity_worker():
            """Worker function to check connectivity in background."""
            try:
                logger.info("[ORCHESTRATOR] Checking connectivity in background thread")
                internet_connected, error_msg = check_internet_connection()
                logger.info(
                    f"[ORCHESTRATOR] Internet check: connected={internet_connected}, error={error_msg}"
                )

                service_results = check_all_services()
                logger.info(f"[ORCHESTRATOR] Service check results: {service_results}")

                problem_services = [
                    service
                    for service, (connected, _) in service_results.items()
                    if not connected
                ]
                logger.info(f"[ORCHESTRATOR] Problem services: {problem_services}")

                # Schedule UI update on main thread
                def update_ui():
                    try:
                        self._handle_connectivity_check(
                            internet_connected, error_msg, problem_services
                        )
                    except Exception as e:
                        logger.error(
                            f"[ORCHESTRATOR] Error handling connectivity results: {e}",
                            exc_info=True,
                        )

                # Use root window's after method to schedule on main thread
                if self.root:
                    self.root.after(0, update_ui)
                else:
                    logger.error("[ORCHESTRATOR] Root window not available")

            except Exception as e:
                logger.error(
                    f"[ORCHESTRATOR] Error in connectivity check: {e}",
                    exc_info=True,
                )

                # Try to update status with error on main thread
                def update_error_status():
                    try:
                        self.event_coordinator.update_status(
                            "Network check failed", is_error=True
                        )
                    except Exception as update_error:
                        logger.error(
                            f"[ORCHESTRATOR] Failed to update status: {update_error}"
                        )

                if self.root:
                    self.root.after(0, update_error_status)

        # Start background thread
        import threading

        thread = threading.Thread(
            target=connectivity_worker, daemon=True, name="ConnectivityCheck"
        )
        thread.start()
        logger.info("[ORCHESTRATOR] Connectivity check started in background thread")

    def _handle_connectivity_check(
        self, internet_connected: bool, error_msg: str, problem_services: list
    ) -> None:
        """Handle connectivity check results."""
        logger.info("[ORCHESTRATOR] Handling connectivity check results - START")
        logger.info(
            f"[ORCHESTRATOR] internet_connected={internet_connected}, problem_services={problem_services}"
        )

        try:
            if not internet_connected:
                logger.warning(f"[ORCHESTRATOR] No internet connection: {error_msg}")
                self.event_coordinator.update_status(
                    "Network connectivity issues detected", is_error=True
                )
                # Show error dialog via message queue instead of blocking messagebox
                self.event_coordinator.show_error(
                    "Network Connectivity Issue",
                    f"There are network connectivity issues:\n\n{error_msg}\n\n"
                    "You can view detailed network status from Tools > Network Status.",
                )
            elif problem_services:
                problem_list = ", ".join([str(s) for s in problem_services])
                logger.warning(f"[ORCHESTRATOR] Problem services: {problem_list}")
                self.event_coordinator.update_status(
                    f"Connection issues with: {problem_list}", is_error=True
                )
                # Show warning dialog via message queue
                try:
                    from src.core.enums.message_level import MessageLevel
                    from src.services.events.queue import Message

                    message_queue = self.container.get("message_queue")
                    if message_queue:
                        message_queue.add_message(
                            Message(
                                text=f"Cannot connect to the following services: {problem_list}\n\n"
                                "You can view detailed network status from Tools > Network Status.",
                                level=MessageLevel.WARNING,
                                title="Service Connection Issues",
                            )
                        )
                except Exception as e:
                    logger.error(f"[ORCHESTRATOR] Failed to show warning dialog: {e}")
            else:
                logger.info("[ORCHESTRATOR] All services connected successfully")
                self.event_coordinator.update_status("Ready - All services connected")

            logger.info("[ORCHESTRATOR] Connectivity check handling complete")
        except Exception as e:
            logger.error(
                f"[ORCHESTRATOR] Error handling connectivity check: {e}", exc_info=True
            )
            # Fallback to simple status update
            try:
                self.event_coordinator.update_status("Ready", is_error=False)
            except Exception as update_error:
                logger.error(
                    f"[ORCHESTRATOR] Failed fallback status update: {update_error}"
                )

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
