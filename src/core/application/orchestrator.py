"""Application Orchestrator - Clean dependency injection initialization."""

import os
import threading
from functools import partial
from typing import Any, Type

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.coordinators.main_coordinator import EventCoordinator
from src.handlers.service_detector import ServiceDetector
from src.interfaces.service_interfaces import (
    IAutoCookieManager,
    ICookieHandler,
    IDownloadHandler,
    IDownloadService,
    IErrorHandler,
    IFileService,
    IMessageQueue,
    IMetadataService,
    INetworkChecker,
    IServiceFactory,
    IUIState,
)
from src.services.cookies import CookieManager as AutoCookieManager
from src.services.detection.link_detector import LinkDetector
from src.services.events.queue import Message, MessageLevel, MessageQueue
from src.services.file import FileService
from src.services.instagram import InstagramAuthManager
from src.services.youtube.cookie_detector import CookieDetector, ICookieDetector
from src.utils.logger import get_logger

from ..models import UIState
from .di_container import ServiceContainer
from .service_factories import ServiceFactoryRegistry

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

    def __init__(self, root_window: ctk.CTk, config: AppConfig | None = None):
        """Initialize orchestrator with root window.
        
        Args:
            root_window: Root Tkinter window
            config: AppConfig instance (defaults to get_config() if None)
        """
        if config is None:
            config = get_config()
        self.config: AppConfig = config
        self.root = root_window
        self.downloads_folder = str(self.config.paths.downloads_dir)
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.ui_state = UIState()

        # Configure DI container - let it handle everything
        self.container = ServiceContainer()
        self.factory_registry = ServiceFactoryRegistry(self.container, self.root)
        self._configure_dependencies()

        # Get injected dependencies
        self.network_checker = self.container.get(INetworkChecker)

        # Initialize link detection and background tasks
        self._import_link_handlers()
        self.link_detector = LinkDetector(handler_factory=self._create_handler_factory())
        logger.info("[ORCHESTRATOR] LinkDetector created with handler factory")
        self._initialize_cookies_background()

        # UI components (set by main.py)
        self.ui_components: dict[str, Any] = {}

        logger.info("[ORCHESTRATOR] Clean initialization complete")

    def _configure_dependencies(self) -> None:
        """Configure all dependency injection mappings."""
        logger.info("[ORCHESTRATOR] Configuring dependencies")

        # Register AppConfig first - many services depend on it
        self.container.register_instance(AppConfig, self.config)

        # Register core services
        self._register_core_services()
        self._register_handlers()
        self._register_services()
        self._register_coordinators()
        self._register_detectors()

        # Validate all dependencies
        try:
            self.container.validate_dependencies()
            logger.info("[ORCHESTRATOR] Dependencies configured and validated")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Dependency validation failed: {e}", exc_info=True)
            raise

    def _register_core_services(self) -> None:
        """Register core application services."""
        # MessageQueue factory returns None initially, replaced when status_bar is available
        self.container.register_factory(IMessageQueue, lambda: None)
        self.container.register_singleton(IFileService, FileService)
        self.container.register_singleton(IAutoCookieManager, AutoCookieManager)
        self.container.register_singleton(InstagramAuthManager, self.factory_registry.create_instagram_auth_manager)
        self.container.register_singleton(IUIState, UIState)
        self.container.register_singleton(UIState, UIState)
        self.container.register_singleton(ServiceDetector)

    def _register_handlers(self) -> None:
        """Register application handlers."""
        self.container.register_singleton(ICookieHandler, self.factory_registry.create_cookie_handler)
        self.container.register_singleton(IErrorHandler, self.factory_registry.create_error_handler)
        self.container.register_singleton(IDownloadHandler, self.factory_registry.create_download_handler)

    def _register_services(self) -> None:
        """Register service implementations."""
        self.container.register_singleton(IMetadataService, self.factory_registry.create_metadata_service)
        self.container.register_singleton(INetworkChecker, self.factory_registry.create_network_checker)
        self.container.register_singleton(IServiceFactory, self.factory_registry.create_service_factory)
        self.container.register_singleton(IDownloadService, self.factory_registry.create_download_service)

    def _register_coordinators(self) -> None:
        """Register coordinators."""
        self.container.register_singleton(
            EventCoordinator,
            lambda: self.factory_registry.create_event_coordinator(self.downloads_folder)
        )

    def _register_detectors(self) -> None:
        """Register detector services."""
        self.container.register_singleton(ICookieDetector, CookieDetector)
        self.container.register_singleton(LinkDetector, LinkDetector)

    def _create_handler_factory(self) -> callable:
        """Create handler factory for LinkDetector."""
        def handler_factory(handler_class: Type) -> Any:
            """Factory function using container's auto-injection capabilities."""
            try:
                instance = self.container.create_with_injection(handler_class)
                logger.debug(f"[ORCHESTRATOR] Auto-injected dependencies for {handler_class.__name__}")
                return instance
            except ValueError as e:
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
        
        return handler_factory

    def _import_link_handlers(self) -> None:
        """Import link handler modules to trigger auto-registration decorators."""
        try:
            from src.handlers import (
                instagram_handler,
                pinterest_handler,
                soundcloud_handler,
                twitter_handler,
                youtube_handler,
            )
            logger.info("[ORCHESTRATOR] Link handler modules imported - auto-registration triggered")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Failed to import link handler modules: {e}", exc_info=True)

    def _initialize_cookies_background(self) -> None:
        """Initialize cookies in background thread to not block startup."""
        def init_cookies():
            """Background task to initialize cookies."""
            try:
                logger.info("[ORCHESTRATOR] Starting background cookie initialization")
                state = self.auto_cookie_manager.initialize()

                if state.is_valid:
                    logger.info("[ORCHESTRATOR] Cookies initialized successfully")
                elif state.error_message:
                    logger.error(f"[ORCHESTRATOR] Cookie initialization failed: {state.error_message}")
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

        thread = threading.Thread(target=init_cookies, daemon=True, name="CookieInit")
        thread.start()
        logger.info("[ORCHESTRATOR] Cookie initialization started in background")

    @property
    def auto_cookie_manager(self) -> IAutoCookieManager:
        """Get auto cookie manager from container."""
        return self.container.get(IAutoCookieManager)

    @property
    def error_handler(self) -> IErrorHandler:
        """Get error handler from container."""
        return self.container.get(IErrorHandler)

    @property
    def event_coordinator(self) -> EventCoordinator:
        """Get event coordinator from container."""
        return self.container.get(EventCoordinator)

    def set_ui_components(self, **components) -> None:
        """Set UI component references."""
        logger.info(f"[ORCHESTRATOR] Setting UI components: {list(components.keys())}")
        self.ui_components.update(components)

        # Register message queue if status_bar is available
        if "status_bar" in components:
            message_queue = MessageQueue(components["status_bar"])
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

        # Set link detector on event coordinator
        if hasattr(self.event_coordinator, 'link_detector'):
            self.event_coordinator.link_detector = self.link_detector

        # Set orchestrator reference on platform dialog coordinator
        if hasattr(self.event_coordinator, 'platform_dialogs'):
            self.event_coordinator.platform_dialogs.orchestrator = self
            logger.info("[ORCHESTRATOR] Set orchestrator reference on PlatformDialogCoordinator")

        # Create thread-safe UI callbacks
        callbacks = self._create_ui_callbacks(components)
        
        if self.event_coordinator:
            self.event_coordinator.set_ui_callbacks(callbacks)
            self.event_coordinator.refresh_handlers()

        logger.info("[ORCHESTRATOR] UI components registered")

    def _create_ui_callbacks(self, components: dict) -> dict:
        """Create thread-safe UI callbacks from components."""
        callbacks = {}

        def safe_ui_update(func, *args, **kwargs):
            """Execute UI update on main thread."""
            # self.root is always MediaDownloaderApp which has run_on_main_thread
            self.root.run_on_main_thread(partial(func, *args, **kwargs))
        
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
            
        return callbacks

    def check_connectivity(self) -> None:
        """Check network connectivity at startup."""
        logger.info("[ORCHESTRATOR] Starting connectivity check")
        
        status_bar = self.ui_components.get("status_bar")
        if status_bar:
            status_bar.show_message("Checking network connection...")

        def check_in_background():
            """Check connectivity in background thread."""
            try:
                is_connected, error_message = self.network_checker.check_connectivity()

                def update_ui():
                    logger.info(f"[ORCHESTRATOR] Connectivity check complete: connected={is_connected}, error={error_message}")
                    self._handle_connectivity_result(is_connected, error_message)

                # self.root is always MediaDownloaderApp which has run_on_main_thread
                self.root.run_on_main_thread(update_ui)
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Error checking connectivity: {e}", exc_info=True)

                def update_ui_error():
                    logger.info(f"[ORCHESTRATOR] Connectivity check error: {str(e)}")
                    self._handle_connectivity_result(False, str(e))

                # self.root is always MediaDownloaderApp which has run_on_main_thread
                self.root.run_on_main_thread(update_ui_error)

        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()

    def _handle_connectivity_result(self, is_connected: bool, error_message: str) -> None:
        """Handle connectivity check result on main thread."""
        logger.info(f"[ORCHESTRATOR] _handle_connectivity_result called: connected={is_connected}, error={error_message}")
        status_bar = self.ui_components.get("status_bar")

        if is_connected:
            logger.info("[ORCHESTRATOR] Connectivity check: Connected")
            if status_bar:
                # Show "Connection confirmed" immediately, then "Ready" after timeout
                status_bar.show_message("Connection confirmed")
        else:
            logger.warning(f"[ORCHESTRATOR] Connectivity check failed: {error_message}")
            if status_bar:
                status_bar.show_warning(f"Network issue: {error_message or 'Connection failed'}")
            if self.container.has(IMessageQueue):
                try:
                    message_queue = self.container.get(IMessageQueue)
                    if message_queue:
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

    def show_network_status(self) -> None:
        """Show network status dialog."""
        self.event_coordinator.show_network_status()
    
    def cleanup(self) -> None:
        """Clean up all services."""
        try:
            logger.info("[ORCHESTRATOR] Cleaning up services")

            if hasattr(self.event_coordinator, 'cleanup'):
                self.event_coordinator.cleanup()

            self.container.clear()

            logger.info("[ORCHESTRATOR] Cleanup complete")
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Error during cleanup: {e}", exc_info=True)
