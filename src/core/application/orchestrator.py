"""Application Orchestrator - Clean dependency injection initialization."""

import os
from typing import Any

import customtkinter as ctk

from src.core.interfaces import (
    IDownloadService,
    IDownloadHandler,
    IServiceFactory,
    IFileService,
    IMessageQueue,
    IErrorHandler,
    IAutoCookieManager,
    ICookieHandler,
    IMetadataService,
    INetworkChecker,
    IUIState,
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
    ICookieDetector,
)
from src.services.youtube.metadata_service import YouTubeMetadataService
from src.handlers.cookie_handler import CookieHandler
from src.handlers.download_handler import DownloadHandler
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
        self.ui_state = UIState()

        # Configure DI container - let it handle everything
        self.container = ServiceContainer()
        self._configure_dependencies()

        # Initialize link detection and background tasks
        self.link_detector = LinkDetector()
        self._import_link_handlers()  # Import handlers to trigger auto-registration decorators
        self._initialize_cookies_background()

        # UI components (set by main.py)
        self.ui_components: dict[str, Any] = {}

        logger.info("[ORCHESTRATOR] Clean initialization complete")

    def _configure_dependencies(self) -> None:
        """Configure all dependency injection mappings - let container handle everything."""
        logger.info("[ORCHESTRATOR] Configuring dependencies")

        # Register core instances
        # Note: Some values like root are passed directly where needed

        # Register interface implementations
        self.container.register_factory(IMessageQueue, lambda: MessageQueue(None))
        self.container.register_singleton(IFileService, FileService)
        self.container.register_singleton(ICookieHandler, CookieHandler)
        self.container.register_singleton(IMetadataService, YouTubeMetadataService)
        self.container.register_singleton(INetworkChecker, NetworkChecker)
        self.container.register_singleton(IAutoCookieManager, AutoCookieManager)
        self.container.register_singleton(IUIState, UIState)
        self.container.register_singleton(UIState, UIState)
        self.container.register_singleton(IDownloadHandler, DownloadHandler)

        # ErrorHandler needs message_queue injected
        def create_error_handler():
            from src.coordinators.error_handler import ErrorHandler
            message_queue = self.container.get(IMessageQueue)
            return ErrorHandler(message_queue)

        self.container.register_factory(IErrorHandler, create_error_handler)

        # Register service implementations
        def create_service_factory():
            from src.services.downloads import ServiceFactory
            cookie_manager = self.container.get(IAutoCookieManager)
            return ServiceFactory(cookie_manager)

        self.container.register_singleton(IServiceFactory, create_service_factory)

        def create_download_service():
            from src.services.downloads import DownloadService
            service_factory = self.container.get(IServiceFactory)
            return DownloadService(service_factory)

        self.container.register_singleton(IDownloadService, create_download_service)
        self.container.register_singleton(ServiceDetector)

        # Handlers are auto-registered via @auto_register_handler decorators
        # The link detector will register all handlers automatically

        # Register coordinators - import EventCoordinator first
        from src.coordinators.main_coordinator import EventCoordinator

        def create_event_coordinator():
            return EventCoordinator(
                root_window=self.root,
                error_handler=self.container.get(IErrorHandler),
                download_handler=self.container.get(IDownloadHandler),
                file_service=self.container.get(IFileService),
                network_checker=self.container.get(INetworkChecker),
                cookie_handler=self.container.get(ICookieHandler),
                download_service=self.container.get(IDownloadService),
                message_queue=self.container.get(IMessageQueue),
                downloads_folder=self.downloads_folder
            )

        self.container.register_singleton(EventCoordinator, create_event_coordinator)

        # Register detector services
        self.container.register_singleton(ICookieDetector, CookieDetector)
        self.container.register_singleton(LinkDetector, LinkDetector)

        # Validate everything can be resolved
        self.container.validate_dependencies()
        logger.info("[ORCHESTRATOR] Dependencies configured and validated")

    
    @property
    def auto_cookie_manager(self) -> IAutoCookieManager:
        """Get auto cookie manager from container."""
        return self.container.get(IAutoCookieManager)

    @property
    def error_handler(self) -> IErrorHandler:
        """Get error handler from container."""
        return self.container.get(IErrorHandler)

    @property
    def event_coordinator(self) -> 'EventCoordinator':
        """Get event coordinator from container."""
        from src.coordinators.main_coordinator import EventCoordinator
        return self.container.get(EventCoordinator)

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

    def _import_link_handlers(self) -> None:
        """Import link handler modules to trigger auto-registration decorators."""
        try:
            # Import handler modules to trigger @auto_register_handler decorators
            # The decorators will automatically register each handler with the LinkDetectionRegistry
            from src.handlers import (
                youtube_handler,
                instagram_handler,
                twitter_handler,
                pinterest_handler,
                soundcloud_handler,
            )

            logger.info("[ORCHESTRATOR] Link handler modules imported - auto-registration triggered")
        except Exception as e:
            logger.error(
                f"[ORCHESTRATOR] Failed to import link handler modules: {e}", exc_info=True
            )

    def set_ui_components(self, **components) -> None:
        """Set UI component references."""
        logger.info(f"[ORCHESTRATOR] Setting UI components: {list(components.keys())}")

        self.ui_components.update(components)

        # UI components are stored in self.ui_components for reference
        # No need to register them in DI container as they're not dependency injected

        # Refresh event coordinator handlers (so it picks up UI components)
        self.event_coordinator.refresh_handlers()

        logger.info("[ORCHESTRATOR] UI components registered")

    # Convenience methods for UI
    def check_connectivity(self) -> None:
        """Check network connectivity at startup - delegate to event coordinator."""
        logger.info("[ORCHESTRATOR] Starting connectivity check")

        # Ensure event coordinator is ready
        if not self.event_coordinator:
            logger.error("[ORCHESTRATOR] Event coordinator not initialized")
            return

        # Delegate to event coordinator - it handles UI components
        self.event_coordinator.check_connectivity()

    def _handle_connectivity_check(
        self, internet_connected: bool, error_msg: str, problem_services: list
    ) -> None:
        """Handle connectivity check results - delegate to event coordinator."""
        logger.info("[ORCHESTRATOR] Handling connectivity check results - START")
        logger.info(
            f"[ORCHESTRATOR] internet_connected={internet_connected}, problem_services={problem_services}"
        )

        try:
            # Delegate to event coordinator - it handles UI updates
            if self.event_coordinator:
                self.event_coordinator.handle_connectivity_results(
                    internet_connected, error_msg, problem_services
                )
            else:
                logger.warning("[ORCHESTRATOR] Event coordinator not available for connectivity results")

            logger.info("[ORCHESTRATOR] Connectivity check handling complete")
        except Exception as e:
            logger.error(
                f"[ORCHESTRATOR] Error handling connectivity check: {e}", exc_info=True
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
