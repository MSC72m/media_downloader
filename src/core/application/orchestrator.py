"""Application Orchestrator - Clean dependency injection initialization."""

import os
from typing import Any, Type
from functools import partial

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

        # Get injected dependencies
        self.network_checker = self.container.get(INetworkChecker)

        # Initialize link detection and background tasks
        # Import handlers first to trigger auto-registration decorators
        self._import_link_handlers()
        
        # Create handler factory that uses container's auto-injection
        # Handlers don't need to be registered - only their dependencies need to be registered
        # The container's create_with_injection will automatically resolve dependencies
        # based on type hints, enabling polymorphic behavior
        def handler_factory(handler_class: Type) -> Any:
            """Factory function using container's auto-injection capabilities.
            
            Uses the container's create_with_injection method which automatically:
            - Resolves type hints from constructor parameters
            - Injects registered dependencies from the container
            - Handles Optional[T] types gracefully
            - Falls back to None for optional dependencies not in container
            
            This enables polymorphic behavior - handlers with different dependency
            requirements are all handled uniformly through the container.
            """
            # Use container's public method for creating instances with injection
            try:
                instance = self.container.create_with_injection(handler_class)
                logger.debug(f"[ORCHESTRATOR] Auto-injected dependencies for {handler_class.__name__}")
                return instance
            except ValueError as e:
                # Dependency not registered - try direct instantiation for handlers without deps
                logger.debug(f"[ORCHESTRATOR] Handler {handler_class.__name__} has unregistered dependencies, trying direct instantiation: {e}")
                try:
                    return handler_class()
                except Exception as fallback_error:
                    logger.error(f"[ORCHESTRATOR] Direct instantiation also failed for {handler_class.__name__}: {fallback_error}")
                    raise
            except Exception as e:
                logger.warning(f"[ORCHESTRATOR] Auto-injection failed for {handler_class.__name__}: {e}, trying direct instantiation")
                try:
                    return handler_class()
                except Exception as fallback_error:
                    logger.error(f"[ORCHESTRATOR] Direct instantiation also failed for {handler_class.__name__}: {fallback_error}")
                    raise
        
        self.link_detector = LinkDetector(handler_factory=handler_factory)
        logger.info("[ORCHESTRATOR] LinkDetector created with handler factory")
        self._initialize_cookies_background()

        # UI components (set by main.py)
        self.ui_components: dict[str, Any] = {}

        logger.info("[ORCHESTRATOR] Clean initialization complete")

    def _configure_dependencies(self) -> None:
        """Configure all dependency injection mappings - let container handle everything."""
        logger.info("[ORCHESTRATOR] Configuring dependencies")

        # Register core instances
        # Note: Some values like root are passed directly where needed

        # Register IMessageQueue factory that returns None initially
        # Will be replaced with actual instance when status_bar is available
        self.container.register_factory(IMessageQueue, lambda: None)
        
        self.container.register_singleton(IFileService, FileService)
        self.container.register_singleton(ICookieHandler, CookieHandler)
        
        def create_metadata_service():
            error_handler = self.container.get_optional(IErrorHandler)
            return YouTubeMetadataService(error_handler=error_handler)
        
        self.container.register_singleton(IMetadataService, create_metadata_service)
        
        def create_network_checker():
            error_handler = self.container.get_optional(IErrorHandler)
            return NetworkChecker(error_handler=error_handler)
        
        self.container.register_singleton(INetworkChecker, create_network_checker)
        self.container.register_singleton(IAutoCookieManager, AutoCookieManager)
        self.container.register_singleton(IUIState, UIState)
        self.container.register_singleton(UIState, UIState)
        
        def create_download_handler():
            return DownloadHandler(
                download_service=self.container.get(IDownloadService),
                service_factory=self.container.get(IServiceFactory),
                file_service=self.container.get(IFileService),
                ui_state=self.container.get(IUIState),
                cookie_handler=self.container.get(ICookieHandler),
                auto_cookie_manager=self.container.get(IAutoCookieManager),
                message_queue=self.container.get_optional(IMessageQueue),
                error_handler=self.container.get_optional(IErrorHandler),
            )
        
        self.container.register_singleton(IDownloadHandler, create_download_handler)

        # ErrorHandler needs message_queue injected
        # Use get_optional since message queue may not be registered yet
        def create_error_handler():
            from src.coordinators.error_handler import ErrorHandler
            message_queue = self.container.get_optional(IMessageQueue)
            return ErrorHandler(message_queue)

        self.container.register_singleton(IErrorHandler, create_error_handler)

        # Register service implementations
        def create_service_factory():
            from src.services.downloads import ServiceFactory
            cookie_manager = self.container.get(IAutoCookieManager)
            error_handler = self.container.get_optional(IErrorHandler)
            return ServiceFactory(cookie_manager, error_handler=error_handler)

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
                message_queue=self.container.get_optional(IMessageQueue),  # Optional - may be None initially
                downloads_folder=self.downloads_folder
            )

        self.container.register_singleton(EventCoordinator, create_event_coordinator)

        # Register detector services
        self.container.register_singleton(ICookieDetector, CookieDetector)
        self.container.register_singleton(LinkDetector, LinkDetector)

        try:
            self.container.validate_dependencies()
            logger.info("[ORCHESTRATOR] Dependencies configured and validated")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Dependency validation failed: {e}", exc_info=True)
            raise

    
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

        # Register message queue if status_bar is available
        # Replace the None factory with actual MessageQueue instance
        if "status_bar" in components:
            from src.services.events.queue import MessageQueue
            message_queue = MessageQueue(components["status_bar"])
            # Replace the factory registration with an instance
            self.container.register_instance(IMessageQueue, message_queue)
            logger.info("[ORCHESTRATOR] MessageQueue registered in container with status_bar")
            
            # Update ErrorHandler with the message queue
            if self.container.has(IErrorHandler):
                try:
                    error_handler = self.container.get(IErrorHandler)
                    error_handler.set_message_queue(message_queue)
                    logger.info("[ORCHESTRATOR] Updated ErrorHandler with MessageQueue")
                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Failed to update ErrorHandler with MessageQueue: {e}")
            
            # Update EventCoordinator with message queue
            if self.event_coordinator:
                self.event_coordinator.set_message_queue(message_queue)

        # Set link detector on event coordinator so it uses the configured instance
        if hasattr(self.event_coordinator, 'link_detector'):
            self.event_coordinator.link_detector = self.link_detector

        # Set orchestrator reference on platform dialog coordinator for UI component access
        if hasattr(self.event_coordinator, 'platform_dialogs'):
            self.event_coordinator.platform_dialogs.orchestrator = self

        # Define thread-safe UI callbacks using partial for cleaner closures

        def safe_ui_update(func, *args, **kwargs):
            """Execute UI update on main thread."""
            if hasattr(self.root, 'run_on_main_thread'):
                self.root.run_on_main_thread(partial(func, *args, **kwargs))
            else:
                self.root.after(0, partial(func, *args, **kwargs))

        callbacks = {}
        
        if "download_list" in components:
            dl_list = components["download_list"]
            callbacks["refresh_download_list"] = partial(safe_ui_update, dl_list.refresh_items)
            callbacks["update_download_progress"] = partial(safe_ui_update, dl_list.update_item_progress)
        
        if "action_buttons" in components:
            buttons = components["action_buttons"]
            callbacks["set_action_buttons_enabled"] = partial(safe_ui_update, buttons.set_enabled)
        
        if "status_bar" in components:
            sb = components["status_bar"]
            
            def update_status_wrapper(msg: str, is_err: bool = False) -> None:
                if is_err:
                    sb.show_error(msg)
                else:
                    sb.show_message(msg)
            
            callbacks["update_status"] = partial(safe_ui_update, update_status_wrapper)
            
        if self.event_coordinator:
            self.event_coordinator.set_ui_callbacks(callbacks)

        # Refresh event coordinator handlers (so it picks up UI components)
        self.event_coordinator.refresh_handlers()

        logger.info("[ORCHESTRATOR] UI components registered")

    # Convenience methods for UI
    def check_connectivity(self) -> None:
        """Check network connectivity at startup - use injected network checker."""
        logger.info("[ORCHESTRATOR] Starting connectivity check")
        
        # Show checking message
        status_bar = self.ui_components.get("status_bar")
        if status_bar:
            status_bar.show_message("Checking network connection...")

        def check_in_background():
            """Check connectivity in background thread."""
            try:
                is_connected, error_message = self.network_checker.check_connectivity()

                # Update UI on main thread - use function to avoid closure issues
                def update_ui():
                    logger.info(
                        f"[ORCHESTRATOR] Connectivity check complete: connected={is_connected}, error={error_message}"
                    )
                    self._handle_connectivity_result(is_connected, error_message)

                if hasattr(self.root, 'run_on_main_thread'):
                    self.root.run_on_main_thread(update_ui)
                else:
                    self.root.after(0, update_ui)
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Error checking connectivity: {e}", exc_info=True)

                # Update UI on main thread - use function to avoid closure issues
                def update_ui_error():
                    logger.info(f"[ORCHESTRATOR] Connectivity check error: {str(e)}")
                    self._handle_connectivity_result(False, str(e))

                if hasattr(self.root, 'run_on_main_thread'):
                    self.root.run_on_main_thread(update_ui_error)
                else:
                    self.root.after(0, update_ui_error)

        import threading
        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()

    def _handle_connectivity_result(self, is_connected: bool, error_message: str) -> None:
        """Handle connectivity check result on main thread."""
        logger.info(f"[ORCHESTRATOR] _handle_connectivity_result called: connected={is_connected}, error={error_message}")
        status_bar = self.ui_components.get("status_bar")
        logger.info(f"[ORCHESTRATOR] Status bar available: {status_bar is not None}")

        if is_connected:
            logger.info("[ORCHESTRATOR] Connectivity check: Connected")
            if status_bar:
                status_bar.show_message("Ready!")
            if self.container.has(IMessageQueue):
                try:
                    message_queue = self.container.get(IMessageQueue)
                    if message_queue:
                        from src.services.events.queue import Message
                        from src.core.enums.message_level import MessageLevel
                        # We can optionally log this but "Ready!" on status bar is usually enough
                        pass
                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Could not send message via queue: {e}")
        else:
            logger.warning(f"[ORCHESTRATOR] Connectivity check failed: {error_message}")
            if status_bar:
                status_bar.show_warning(f"Network issue: {error_message or 'Connection failed'}")
            if self.container.has(IMessageQueue):
                try:
                    message_queue = self.container.get(IMessageQueue)
                    if message_queue:
                        from src.services.events.queue import Message
                        from src.core.enums.message_level import MessageLevel
                        message_queue.add_message(
                            Message(
                                text=error_message or "Network connection failed",
                                level=MessageLevel.WARNING,
                                title="Network Status",
                            )
                        )
                except Exception as e:
                    logger.warning(f"[ORCHESTRATOR] Could not send message via queue: {e}")

            if self.event_coordinator:
                self.event_coordinator.show_network_status()

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
