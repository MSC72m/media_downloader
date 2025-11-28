"""Application Orchestrator - Clean dependency injection initialization."""

import os
import threading
from functools import partial
from typing import TYPE_CHECKING, Any

from src.coordinators.main_coordinator import EventCoordinator
from src.core.config import AppConfig, get_config
from src.core.interfaces import (
    IAutoCookieManager,
    ICookieHandler,
    IDownloadHandler,
    IDownloadService,
    IErrorNotifier,
    IFileService,
    IMessageQueue,
    IMetadataService,
    INetworkChecker,
    IServiceFactory,
    IUIState,
)
from src.handlers.service_detector import ServiceDetector
from src.services.cookies import CookieManager as AutoCookieManager
from src.services.detection.link_detector import LinkDetector
from src.services.events.queue import Message, MessageLevel, MessageQueue
from src.services.file import FileService
from src.services.instagram.auth_manager import InstagramAuthManager

if TYPE_CHECKING:
    import customtkinter as ctk

from src.application.di_container import ServiceContainer
from src.application.service_factories import ServiceFactoryRegistry
from src.core.models import UIState
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ApplicationOrchestrator:
    def __init__(self, root_window: "ctk.CTk", config: AppConfig | None = None):
        if config is None:
            config = get_config()
        self.config: AppConfig = config
        self.root = root_window
        self.downloads_folder = str(self.config.paths.downloads_dir)
        os.makedirs(self.downloads_folder, exist_ok=True)
        self.ui_state = UIState()

        self.container = ServiceContainer()
        self.factory_registry = ServiceFactoryRegistry(self.container, self.root)
        self._configure_dependencies()

        self.network_checker = self.container.get(INetworkChecker)

        self._import_link_handlers()
        self.link_detector = LinkDetector(handler_factory=self._create_handler_factory())
        self._initialize_cookies_background()

        self.ui_components: dict[str, Any] = {}

    def _configure_dependencies(self) -> None:
        self.container.register_instance(AppConfig, self.config)

        self._register_core_services()
        self._register_handlers()
        self._register_services()
        self._register_coordinators()
        self._register_detectors()

        try:
            self.container.validate_dependencies()
        except Exception:
            raise

    def _register_core_services(self) -> None:
        self.container.register_factory(IMessageQueue, lambda: None)
        self.container.register_singleton(IFileService, FileService)
        self.container.register_singleton(IAutoCookieManager, AutoCookieManager)
        self.container.register_singleton(
            InstagramAuthManager, self.factory_registry.create_instagram_auth_manager
        )
        self.container.register_singleton(IUIState, UIState)
        self.container.register_singleton(UIState, UIState)
        self.container.register_singleton(ServiceDetector)

    def _register_handlers(self) -> None:
        self.container.register_singleton(
            ICookieHandler, self.factory_registry.create_cookie_handler
        )
        self.container.register_singleton(
            IErrorNotifier, self.factory_registry.create_error_handler
        )
        self.container.register_singleton(
            IDownloadHandler, self.factory_registry.create_download_handler
        )

    def _register_services(self) -> None:
        self.container.register_singleton(
            IMetadataService, self.factory_registry.create_metadata_service
        )
        self.container.register_singleton(
            INetworkChecker, self.factory_registry.create_network_checker
        )
        self.container.register_singleton(
            IServiceFactory, self.factory_registry.create_service_factory
        )
        self.container.register_singleton(
            IDownloadService, self.factory_registry.create_download_service
        )

    def _register_coordinators(self) -> None:
        self.container.register_singleton(
            EventCoordinator,
            lambda: self.factory_registry.create_event_coordinator(self.downloads_folder),
        )

    def _register_detectors(self) -> None:
        self.container.register_singleton(LinkDetector, LinkDetector)

    def _create_handler_factory(self) -> callable:
        def handler_factory(handler_class: type) -> Any:
            try:
                return self.container.create_with_injection(handler_class)
            except ValueError:
                try:
                    return handler_class()
                except Exception:
                    raise
            except Exception:
                try:
                    return handler_class()
                except Exception:
                    raise

        return handler_factory

    def _import_link_handlers(self) -> None:
        import contextlib

        with contextlib.suppress(Exception):
            from src.handlers import (
                instagram_handler,  # noqa: F401
                pinterest_handler,  # noqa: F401
                soundcloud_handler,  # noqa: F401
                twitter_handler,  # noqa: F401
                youtube_handler,  # noqa: F401
            )

    def _initialize_cookies_background(self) -> None:
        def init_cookies():
            try:
                state = self.auto_cookie_manager.initialize()

                if state.is_valid:
                    pass
                elif state.error_message and "Playwright is not installed" in state.error_message:
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
            except Exception as e:
                logger.debug(f"Error in cookie initialization: {e}")

        thread = threading.Thread(target=init_cookies, daemon=True, name="CookieInit")
        thread.start()

    @property
    def auto_cookie_manager(self) -> IAutoCookieManager:
        return self.container.get(IAutoCookieManager)

    @property
    def error_handler(self) -> IErrorNotifier:
        return self.container.get(IErrorNotifier)

    @property
    def event_coordinator(self) -> EventCoordinator:
        return self.container.get(EventCoordinator)

    def set_ui_components(self, **components) -> None:
        self.ui_components.update(components)

        if "status_bar" in components:
            message_queue = MessageQueue(components["status_bar"])
            self.container.register_instance(IMessageQueue, message_queue)

            if self.container.has(IErrorNotifier):
                try:
                    error_handler = self.container.get(IErrorNotifier)
                    error_handler.set_message_queue(message_queue)
                except Exception as e:
                    logger.debug(f"Error setting message queue: {e}")

            if self.event_coordinator:
                self.event_coordinator.set_message_queue(message_queue)

        if hasattr(self.event_coordinator, "link_detector"):
            self.event_coordinator.link_detector = self.link_detector

        if hasattr(self.event_coordinator, "platform_dialogs"):
            self.event_coordinator.platform_dialogs.orchestrator = self

        callbacks = self._create_ui_callbacks(components)

        if self.event_coordinator:
            self.event_coordinator.set_ui_callbacks(callbacks)
            self.event_coordinator.refresh_handlers()

    def _create_ui_callbacks(self, components: dict) -> dict:
        callbacks = {}

        def safe_ui_update(func, *args, **kwargs):
            self.root.run_on_main_thread(partial(func, *args, **kwargs))

        if "download_list" in components:
            dl_list = components["download_list"]
            callbacks["refresh_download_list"] = partial(safe_ui_update, dl_list.refresh_items)
            callbacks["update_download_progress"] = partial(
                safe_ui_update, dl_list.update_item_progress
            )

        if "action_buttons" in components:
            buttons = components["action_buttons"]
            callbacks["set_action_buttons_enabled"] = partial(safe_ui_update, buttons.set_enabled)

        if "status_bar" in components:
            sb = components["status_bar"]

            def update_status_wrapper(msg: str, is_error: bool = False) -> None:
                if is_error:
                    sb.show_error(msg)
                else:
                    sb.show_message(msg)

            callbacks["update_status"] = partial(safe_ui_update, update_status_wrapper)

            # Add direct progress update callback for faster updates
            def update_progress_wrapper(progress: float) -> None:
                sb.update_progress(progress)

            callbacks["update_status_progress"] = partial(safe_ui_update, update_progress_wrapper)

        return callbacks

    def check_connectivity(self) -> None:
        status_bar = self.ui_components.get("status_bar")
        if status_bar:
            status_bar.show_message("Checking network connection...")

        def check_in_background():
            try:
                is_connected, error_message = self.network_checker.check_connectivity()

                def update_ui():
                    self._handle_connectivity_result(is_connected, error_message)

                self.root.run_on_main_thread(update_ui)
            except Exception as e:
                error_msg = str(e)

                def update_ui_error():
                    self._handle_connectivity_result(False, error_msg)

                self.root.run_on_main_thread(update_ui_error)

        thread = threading.Thread(target=check_in_background, daemon=True)
        thread.start()

    def _handle_connectivity_result(self, is_connected: bool, error_message: str) -> None:
        status_bar = self.ui_components.get("status_bar")

        if is_connected:
            if status_bar:
                status_bar.show_message("Connection confirmed")
        else:
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
                except Exception:
                    pass

            if self.event_coordinator:
                self.event_coordinator.show_network_status()

    def show_network_status(self) -> None:
        self.event_coordinator.show_network_status()

    def cleanup(self) -> None:
        try:
            if hasattr(self.event_coordinator, "cleanup"):
                self.event_coordinator.cleanup()

            self.container.clear()
        except Exception:
            pass
