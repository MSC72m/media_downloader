"""Service factory utilities for dependency injection."""

from typing import Any, Callable, Optional, Type

from src.coordinators.error_notifier import ErrorNotifier
from src.coordinators.main_coordinator import EventCoordinator
from src.handlers.cookie_handler import CookieHandler
from src.handlers.download_handler import DownloadHandler
from src.handlers.network_checker import NetworkChecker
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
from src.services.downloads import DownloadService, ServiceFactory
from src.services.instagram import InstagramAuthManager
from src.services.youtube.metadata_service import YouTubeMetadataService
from src.core.config import AppConfig
from src.application.di_container import ServiceContainer


class ServiceFactoryRegistry:
    """Registry for service factory functions to reduce orchestrator complexity."""

    def __init__(self, container: ServiceContainer, root_window: Any):
        """Initialize factory registry.

        Args:
            container: Dependency injection container
            root_window: Root Tkinter window
        """
        self.container = container
        self.root_window = root_window

    def create_cookie_handler(self) -> CookieHandler:
        """Factory for CookieHandler."""
        config = self.container.get(AppConfig)
        return CookieHandler(config=config)

    def create_error_handler(self) -> ErrorNotifier:
        """Factory for ErrorNotifier."""
        message_queue = self.container.get_optional(IMessageQueue)
        return ErrorNotifier(message_queue)

    def create_metadata_service(self) -> YouTubeMetadataService:
        """Factory for YouTubeMetadataService."""
        error_handler = self.container.get_optional(IErrorNotifier)
        return YouTubeMetadataService(error_handler=error_handler)

    def create_network_checker(self) -> NetworkChecker:
        """Factory for NetworkChecker."""
        error_handler = self.container.get_optional(IErrorNotifier)
        return NetworkChecker(error_handler=error_handler)

    def create_instagram_auth_manager(self) -> InstagramAuthManager:
        """Factory for InstagramAuthManager."""
        error_handler = self.container.get_optional(IErrorNotifier)
        config = self.container.get(AppConfig)
        return InstagramAuthManager(error_handler=error_handler, config=config)

    def create_service_factory(self) -> ServiceFactory:
        """Factory for ServiceFactory."""
        from src.core.config import get_config
        cookie_manager = self.container.get(IAutoCookieManager)
        error_handler = self.container.get_optional(IErrorNotifier)
        file_service = self.container.get(IFileService)
        instagram_auth_manager = self.container.get_optional(InstagramAuthManager)
        config = get_config()
        return ServiceFactory(cookie_manager, error_handler=error_handler, instagram_auth_manager=instagram_auth_manager, file_service=file_service, config=config)

    def create_download_service(self) -> DownloadService:
        """Factory for DownloadService."""
        service_factory = self.container.get(IServiceFactory)
        return DownloadService(service_factory)

    def create_download_handler(self) -> DownloadHandler:
        """Factory for DownloadHandler."""
        return DownloadHandler(
            download_service=self.container.get(IDownloadService),
            service_factory=self.container.get(IServiceFactory),
            file_service=self.container.get(IFileService),
            ui_state=self.container.get(IUIState),
            cookie_handler=self.container.get(ICookieHandler),
            auto_cookie_manager=self.container.get(IAutoCookieManager),
            message_queue=self.container.get_optional(IMessageQueue),
            error_handler=self.container.get_optional(IErrorNotifier),
        )

    def create_event_coordinator(self, downloads_folder: str) -> EventCoordinator:
        """Factory for EventCoordinator."""
        instagram_auth_manager = self.container.get_optional(InstagramAuthManager)
        return EventCoordinator(
            root_window=self.root_window,
            error_handler=self.container.get(IErrorNotifier),
            download_handler=self.container.get(IDownloadHandler),
            file_service=self.container.get(IFileService),
            network_checker=self.container.get(INetworkChecker),
            cookie_handler=self.container.get(ICookieHandler),
            download_service=self.container.get(IDownloadService),
            message_queue=self.container.get_optional(IMessageQueue),
            downloads_folder=downloads_folder,
            instagram_auth_manager=instagram_auth_manager,
        )

