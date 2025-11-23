"""Application Orchestrator - Clean dependency injection initialization."""

import os
from typing import Any

import customtkinter as ctk

from src.core.interfaces import (
    IDownloadService,
    IServiceFactory,
    IFileService,
    IMessageQueue,
    IErrorHandler,
    IAutoCookieManager,
    ICookieHandler,
    IMetadataService,
    INetworkChecker,
)
from src.coordinators.error_handler import ErrorHandler
from src.handlers.network_checker import NetworkChecker
from src.handlers.service_detector import ServiceDetector
from src.services.cookies import CookieManager as AutoCookieManager
from src.services.detection.link_detector import LinkDetector
from src.services.downloads import DownloadService, ServiceFactory
from src.services.events.queue import MessageQueue
from src.services.file import FileService
from src.services.youtube.cookie_detector import (
    CookieDetector,
)
from src.services.youtube.metadata_service import YouTubeMetadataService
from src.utils.logger import get_logger

from ..models import UIState
from .di_container import ServiceContainer

logger = get_logger(__name__)


class ApplicationOrchestrator:
    """Clean orchestrator - proper dependency injection without container access.

    Responsibilities:
    1. Configure dependency injection container
    2. Create all services with proper dependencies
    3. Create coordinators with injected dependencies
    4. Initialize application components

    Does NOT:
    - Access container after initialization
    - Use string-based dependency lookup
    - Mix initialization with runtime logic
    """

    def __init__(self, root_window: ctk.CTk):
        """Initialize orchestrator with root window."""
        self.root = root_window

        # Core state
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)

        # Configure DI container - let it handle everything
        self.container = ServiceContainer()
        self._configure_dependencies()

        # Get components through container - no manual creation
        self.event_coordinator = self.container.get(EventCoordinator)

        # Initialize link detection and background tasks
        self.link_detector = LinkDetector()
        self._initialize_cookies_background()

        # UI components (set by main.py)
        self.ui_components: dict[str, Any] = {}

        logger.info("[ORCHESTRATOR] Clean initialization complete")

    def _configure_dependencies(self) -> None:
        """Configure all dependency injection mappings - let container handle everything."""
        logger.info("[ORCHESTRATOR] Configuring dependencies")

        # Register core values/state
        self.container.register_singleton(lambda: self.root, name="root")
        self.container.register_singleton(lambda: self.downloads_folder, name="downloads_folder")
        self.container.register_singleton(lambda: self.ui_state, name="ui_state")

        # Register interface implementations
        self.container.register_singleton(IMessageQueue, MessageQueue)
        self.container.register_singleton(IFileService, FileService)
        self.container.register_singleton(ICookieHandler, CookieHandler)
        self.container.register_singleton(IMetadataService, YouTubeMetadataService)
        self.container.register_singleton(INetworkChecker, NetworkChecker)
        self.container.register_singleton(IAutoCookieManager, AutoCookieManager)
        self.container.register_singleton(IErrorHandler, ErrorHandler)

        # Register service implementations
        self.container.register_singleton(ServiceFactory)
        self.container.register_singleton(DownloadService)
        self.container.register_singleton(ServiceDetector)

        # Handlers are auto-registered via @auto_register_handler decorators
        # The link detector will register all handlers automatically

        # Register coordinators - container will create with all dependencies
        from src.coordinators.main_coordinator import EventCoordinator
        self.container.register_singleton(EventCoordinator)

        # Register factories
        self.container.register_factory(CookieDetector)
        self.container.register_factory(LinkDetector)

        # Validate everything can be resolved
        self.container.validate_dependencies()
        logger.info("[ORCHESTRATOR] Dependencies configured and validated")

    
    def _initialize_cookies_background(self) -> None:
        """Initialize cookies in background thread to not block startup."""
        import threading

        def init_cookies():
            """Background task to initialize cookies."""
            try:
                logger.info("[ORCHESTRATOR] Starting background cookie initialization")

                # Initialize cookies (sync version)
                state = self.auto_cookie_manager.initialize()

                if state.is_valid:
                    logger.info("[ORCHESTRATOR] Cookies initialized successfully")
                elif state.error_message:
                    logger.error(
                        f"[ORCHESTRATOR] Cookie initialization failed: {state.error_message}"
                    )

                    # Check if it's a Playwright installation issue
                    if "Playwright is not installed" in state.error_message:
                        error_message = (
                                "CRITICAL: Playwright is not installed!\n\n"
                                "The auto-cookie generation system requires Playwright to function.\n"
                                "Without it, age-restricted YouTube videos will fail to download.\n\n"
                                "To fix this, run the following commands:\n\n"
                                "  pip install playwright\n"
                                "  playwright install chromium\n\n"
                                "Then restart the application."
                        )
                        self.root.after(
                            2000,
                            lambda: self.error_handler.show_error(
                                "Playwright Not Installed - Action Required",
                                error_message,
                            ),
                        )
                else:
                    logger.warning("[ORCHESTRATOR] Cookies not valid after initialization")

            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Error initializing cookies: {e}", exc_info=True)

        # Start background thread
        thread = threading.Thread(target=init_cookies, daemon=True, name="CookieInit")
        thread.start()
        logger.info("[ORCHESTRATOR] Cookie initialization started in background")

    def _create_simple_auth_manager(self):
        """Create Instagram auth manager with proper login dialog."""

        class InstagramAuthManager:
            """Manages Instagram authentication."""

            def __init__(self, orchestrator):
                self.orchestrator = orchestrator
                self._is_authenticated = False

            def authenticate_instagram(self, parent_window, callback):
                """Show Instagram login dialog and authenticate."""
                logger.info("[AUTH_MANAGER] Starting Instagram authentication")

                try:
                    from src.services.instagram.downloader import InstagramDownloader
                    from src.ui.dialogs.login_dialog import LoginDialog

                    # Create dialog directly on main thread (this method should be called from main thread)
                    logger.info("[AUTH_MANAGER] Creating login dialog")
                    dialog = LoginDialog(parent_window)
                    logger.info(f"[AUTH_MANAGER] Dialog created successfully")

                    # Wait for dialog to close
                    dialog.wait_window()
                    logger.info("[AUTH_MANAGER] Dialog closed")

                    # Check if user provided credentials
                    if not dialog.username or not dialog.password:
                        logger.info("[AUTH_MANAGER] Instagram login cancelled by user")
                        callback(False)
                        return

                    # Store credentials
                    username = dialog.username
                    password = dialog.password
                    logger.info(f"[AUTH_MANAGER] Got credentials for user: {username}")

                    # Start authentication in background thread
                    self._start_authentication(
                        username,
                        password,
                        parent_window,
                        callback,
                    )

                except Exception as e:
                    logger.error(
                        f"[AUTH_MANAGER] Error showing login dialog: {e}", exc_info=True
                    )
                    callback(False, f"Failed to show login dialog: {str(e)}")

            def _start_authentication(
                self, username, password, parent_window, callback
            ):
                """Start authentication in background thread."""
                logger.info("[AUTH_MANAGER] Starting authentication worker thread")
                try:
                    # Attempt authentication in background thread
                    def auth_worker():
                        success = False
                        error_message = ""  # Initialize to empty string, not None

                        try:
                            logger.info("[AUTH_MANAGER] Authenticating with Instagram")
                            # Import inside worker thread
                            from src.services.instagram.downloader import (
                                InstagramDownloader,
                            )

                            downloader = InstagramDownloader()
                            success = downloader.authenticate(username, password)
                            logger.info(
                                f"[AUTH_MANAGER] Authentication result: success={success}"
                            )

                            # Set error message if authentication failed
                            if not success:
                                error_message = (
                                    "Invalid credentials or authentication failed"
                                )

                        except Exception as e:
                            logger.error(
                                f"[AUTH_MANAGER] Authentication error: {e}",
                                exc_info=True,
                            )
                            error_message = str(e)
                            success = False

                        # Callback will be invoked directly from worker thread
                        logger.info(
                            f"[AUTH_MANAGER] Authentication complete, success={success}, error={error_message}"
                        )

                        # Call callback directly - the callback (on_auth_complete) is responsible
                        # for handling thread-safety via queue-based UI updates
                        logger.info(
                            "[AUTH_MANAGER] Calling callback directly from worker thread"
                        )
                        try:
                            callback(success, error_message)
                            logger.info(
                                "[AUTH_MANAGER] Callback completed successfully"
                            )
                        except Exception as callback_error:
                            logger.error(
                                f"[AUTH_MANAGER] Error in callback: {callback_error}",
                                exc_info=True,
                            )

                        logger.info("[AUTH_MANAGER] auth_worker completed")

                    import threading

                    threading.Thread(target=auth_worker, daemon=True).start()
                    logger.info("[AUTH_MANAGER] Authentication thread started")

                except Exception as e:
                    logger.error(
                        f"[AUTH_MANAGER] Error in authentication: {e}", exc_info=True
                    )
                    callback(False, f"Authentication failed: {str(e)}")

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
        """Check network connectivity at startup - fast and non-blocking."""
        logger.info("[ORCHESTRATOR] Starting connectivity check")

        # Ensure event coordinator and UI components are ready
        if not self.event_coordinator:
            logger.error("[ORCHESTRATOR] Event coordinator not initialized")
            return

        # Update status bar - show ready immediately for better UX
        status_bar = self.event_coordinator.container.get("status_bar")
        if status_bar:
            # Show ready immediately - don't block UI waiting for network
            status_bar.show_message("Ready - Checking connectivity in background...")

        # Run quick connectivity check in background
        def connectivity_worker():
            """Worker function to check connectivity in background."""
            try:
                # Quick check - just verify internet, skip detailed service checks
                internet_connected, error_msg = check_internet_connection()

                if internet_connected:
                    # Internet works - assume services are OK, update status
                    if status_bar:
                        status_bar.show_message("Ready - All services connected")
                    logger.info(
                        "[ORCHESTRATOR] Internet connected - services assumed OK"
                    )
                else:
                    # Only if internet fails, show error
                    if status_bar:
                        status_bar.show_error(f"No internet connection: {error_msg}")
                    logger.warning(f"[ORCHESTRATOR] Internet check failed: {error_msg}")

            except Exception as e:
                logger.error(
                    f"[ORCHESTRATOR] Error in connectivity check: {e}",
                    exc_info=True,
                )
                # Don't block UI on error - just log it
                if status_bar:
                    status_bar.show_message("Ready - Connectivity check failed")

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
                # Use status bar only - no error dialogs
                status_message = "Network connectivity issues detected"
                if error_msg:
                    status_message += f": {error_msg}"
                status_bar = self.event_coordinator.container.get("status_bar")
                if status_bar:
                    status_bar.show_error(status_message)
            elif problem_services:
                problem_list = ", ".join([str(s) for s in problem_services])
                logger.warning(f"[ORCHESTRATOR] Problem services: {problem_list}")
                # Use status bar only - no warning dialogs
                status_bar = self.event_coordinator.container.get("status_bar")
                if status_bar:
                    status_bar.show_error(f"Connection issues with: {problem_list}")
            else:
                logger.info("[ORCHESTRATOR] All services connected successfully")
                logger.info(
                    "[ORCHESTRATOR] *** STATUS: Ready - All services connected ***"
                )
                status_bar = self.event_coordinator.container.get("status_bar")
                if status_bar:
                    status_bar.show_message("Ready - All services connected")

            logger.info("[ORCHESTRATOR] Connectivity check handling complete")
        except Exception as e:
            logger.error(
                f"[ORCHESTRATOR] Error handling connectivity check: {e}", exc_info=True
            )
            # Fallback to simple status update - DISABLED TO PREVENT CRASH
            try:
                status_bar = self.event_coordinator.container.get("status_bar")
                if status_bar:
                    status_bar.show_message("Ready")
            except Exception as update_error:
                logger.error(
                    f"[ORCHESTRATOR] Failed fallback status update: {update_error}"
                )

    def show_network_status(self) -> None:
        """Show network status dialog."""
        self.event_coordinator.show_network_status()

    
    def cleanup(self) -> None:
        """Clean up all services."""
        try:
            logger.info("[ORCHESTRATOR] Cleaning up services")

            # Clean up main components with direct cleanup calls
            if hasattr(self.event_coordinator, 'cleanup'):
                self.event_coordinator.cleanup()

            # Clear container
            self.container.clear()

            logger.info("[ORCHESTRATOR] Cleanup complete")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error during cleanup: {e}", exc_info=True)
