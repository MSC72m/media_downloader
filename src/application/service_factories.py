from collections.abc import Callable
from typing import TYPE_CHECKING, cast, overload

from src.application.di_container import ServiceContainer
from src.application.service_factory import ServiceFactory
from src.coordinators.error_notifier import ErrorNotifier
from src.coordinators.main_coordinator import EventCoordinator
from src.core.config import AppConfig
from src.core.enums.service_type import ServiceType
from src.core.interfaces import (
    BaseDownloader,
    IAutoCookieManager,
    ICookieHandler,
    IDownloadHandler,
    IErrorNotifier,
    IFileService,
    IMessageQueue,
    INetworkChecker,
    IUIState,
)
from src.handlers.cookie_handler import CookieHandler
from src.handlers.download_handler import DownloadHandler
from src.handlers.network_checker import NetworkChecker
from src.services.detection.base_handler import BaseHandler
from src.services.instagram import InstagramAuthManager
from src.services.youtube.metadata_service import YouTubeMetadataService
from src.utils.logger import get_logger

if TYPE_CHECKING:
    import customtkinter as ctk

logger = get_logger(__name__)


class ServiceFactoryRegistry:
    def __init__(self, container: ServiceContainer, root_window: "ctk.CTk") -> None:
        self.container = container
        self.root_window = root_window

    @overload
    def _import_class(
        self,
        module_path: str,
        class_name: str,
        expected_type: type[BaseDownloader],
    ) -> type[BaseDownloader] | None: ...

    @overload
    def _import_class(
        self,
        module_path: str,
        class_name: str,
        expected_type: type[BaseHandler],
    ) -> type[BaseHandler] | None: ...

    def _import_class(
        self,
        module_path: str,
        class_name: str,
        expected_type: type[BaseHandler] | type[BaseDownloader],
    ) -> type[BaseHandler] | type[BaseDownloader] | None:
        try:
            module = __import__(module_path, fromlist=[module_path.rsplit(".", 1)[0]])
            imported = getattr(module, class_name, None)
            if isinstance(imported, type) and issubclass(imported, expected_type):
                return imported
            logger.error(
                "%s.%s is not a %s implementation", module_path, class_name, expected_type.__name__
            )
            return None
        except Exception as e:
            logger.error(f"Failed to import {class_name} from {module_path}: {e}")
            return None

    def _import_downloader_class(
        self,
        module_path: str,
        class_name: str,
    ) -> type[BaseDownloader] | None:
        """Dynamically import downloader class.

        Args:
            module_path: Module path (e.g., "src.services.spotify.downloader")
            class_name: Class name to import

        Returns:
            Downloader class or None
        """
        return self._import_class(module_path, class_name, BaseDownloader)

    def _import_handler_class(self, module_path: str, class_name: str) -> type[BaseHandler] | None:
        """Dynamically import handler class.

        Args:
            module_path: Module path (e.g., "src.handlers.spotify_handler")
            class_name: Class name to import

        Returns:
            Handler class or None
        """
        return self._import_class(module_path, class_name, BaseHandler)

    def create_downloader(self, service_type: str) -> BaseDownloader | None:
        """Create downloader instance dynamically from service config.

        Args:
            service_type: Service type string (e.g., "youtube", "spotify")

        Returns:
            Downloader instance or None
        """
        config = self.container.get(AppConfig)
        if not (service_config := getattr(config.services, service_type, None)):
            logger.error(f"No service configuration found for: {service_type}")
            return None

        downloader_class = self._import_downloader_class(
            service_config["downloader_module"], service_config["downloader_class"]
        )

        if not downloader_class:
            return None

        downloader_ctor = cast(Callable[..., BaseDownloader], downloader_class)
        return downloader_ctor(
            error_handler=self.container.get_optional(IErrorNotifier),
            file_service=self.container.get(IFileService),
            config=config,
        )

    def create_handler(
        self, service_type: str, message_queue: IMessageQueue | None
    ) -> BaseHandler | None:
        """Create handler instance dynamically from service config.

        Args:
            service_type: Service type string (e.g., "youtube", "spotify")
            message_queue: Message queue instance

        Returns:
            Handler instance or None
        """
        config = self.container.get(AppConfig)
        if not (service_config := getattr(config.services, service_type, None)):
            logger.error(f"No service configuration found for: {service_type}")
            return None

        handler_class = self._import_handler_class(
            service_config["handler_module"], service_config["handler_class"]
        )

        if not handler_class:
            return None

        handler_ctor = cast(Callable[..., BaseHandler], handler_class)
        return handler_ctor(message_queue=message_queue, config=config)

    def create_download_handler(self) -> DownloadHandler:
        """Create download handler with proper dependencies."""
        return DownloadHandler(
            service_factory=self._get_service_factory(),
            file_service=self.container.get(IFileService),
            ui_state=self.container.get(IUIState),
            cookie_handler=self.container.get(ICookieHandler),
            auto_cookie_manager=self.container.get(IAutoCookieManager),
            message_queue=self.container.get_optional(IMessageQueue),
            error_handler=self.container.get_optional(IErrorNotifier),
        )

    def _get_service_factory(self) -> ServiceFactory:
        """Get or create ServiceFactory using new registry."""
        return ServiceFactory(
            cookie_handler=self.container.get_optional(ICookieHandler),
            auto_cookie_manager=self.container.get_optional(IAutoCookieManager),
            error_handler=self.container.get_optional(IErrorNotifier),
            file_service=self.container.get(IFileService),
            config=self.container.get(AppConfig),
        )

    def create_event_coordinator(self, downloads_folder: str) -> EventCoordinator:
        """Create event coordinator with all dependencies."""
        instagram_auth_manager = self.container.get_optional(InstagramAuthManager)

        network_checker = self.container.get_optional(INetworkChecker)
        return EventCoordinator(
            root_window=self.root_window,
            error_handler=self.container.get(IErrorNotifier),
            download_handler=self.container.get(IDownloadHandler),
            file_service=self.container.get(IFileService),
            network_checker=network_checker if network_checker else MockINetworkChecker(),
            cookie_handler=self.container.get(ICookieHandler),
            message_queue=self.container.get_optional(IMessageQueue),
            downloads_folder=downloads_folder,
            instagram_auth_manager=instagram_auth_manager,
        )

    def create_instagram_auth_manager(self) -> InstagramAuthManager:
        """Create Instagram auth manager."""
        return InstagramAuthManager(
            config=self.container.get(AppConfig),
            error_handler=self.container.get_optional(IErrorNotifier),
        )

    def create_cookie_handler(self) -> CookieHandler:
        """Create cookie handler."""
        return CookieHandler(config=self.container.get(AppConfig))

    def create_error_handler(self) -> ErrorNotifier:
        """Create error handler/notifier."""
        return ErrorNotifier()

    def create_metadata_service(self) -> YouTubeMetadataService:
        """Create metadata service."""
        return YouTubeMetadataService(
            error_handler=self.container.get_optional(IErrorNotifier),
            auto_cookie_manager=self.container.get_optional(IAutoCookieManager),
            cookie_handler=self.container.get_optional(ICookieHandler),
            config=self.container.get(AppConfig),
        )

    def create_network_checker(self) -> INetworkChecker:
        """Create network checker or mock."""
        return self.container.get_optional(NetworkChecker) or NetworkChecker(
            error_handler=self.container.get_optional(IErrorNotifier)
        )

    def create_service_factory(self) -> ServiceFactory:
        """Create service factory instance."""
        return ServiceFactory(
            cookie_handler=self.container.get_optional(ICookieHandler),
            auto_cookie_manager=self.container.get_optional(IAutoCookieManager),
            error_handler=self.container.get_optional(IErrorNotifier),
            file_service=self.container.get(IFileService),
            config=self.container.get(AppConfig),
        )


class MockINetworkChecker:
    """Mock network checker for optional dependencies."""

    def check_connectivity(self) -> tuple[bool, str]:
        return True, ""

    def check_internet_connection(self) -> tuple[bool, str]:
        return True, ""

    def check_service_connection(self, service: ServiceType) -> tuple[bool, str]:
        return True, ""

    def get_problem_services(self) -> list[ServiceType]:
        return []
