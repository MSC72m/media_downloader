"""Tests for the application orchestration system."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.core.application.orchestrator import ApplicationOrchestrator
from src.core.application.di_container import ServiceContainer, LifetimeScope
from src.core.interfaces import (
    IDownloadService,
    IDownloadHandler,
    ICookieHandler,
    IMetadataService,
    INetworkChecker,
    IErrorHandler,
    IAutoCookieManager,
    IFileService,
    IMessageQueue,
    IServiceFactory,
    IUIState,
)
from src.services.events.event_bus import DownloadEventBus


class MockErrorHandler(IErrorHandler):
    """Mock error handler for testing."""

    def show_error(self, title: str, message: str) -> None:
        pass

    def show_warning(self, title: str, message: str) -> None:
        pass

    def show_info(self, title: str, message: str) -> None:
        pass


class MockDownloadHandler(IDownloadHandler):
    """Mock download handler for testing."""

    def process_url(self, url: str, options: dict = None) -> bool:
        return True

    def handle_download_error(self, error: Exception) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def add_download(self, download) -> None:
        pass

    def remove_downloads(self, indices: list) -> None:
        pass

    def clear_downloads(self) -> None:
        pass

    def start_downloads(self, downloads: list, download_dir: str, progress_callback=None, completion_callback=None) -> None:
        pass

    def cancel_download(self, download) -> None:
        pass


class MockDownloadService(IDownloadService):
    """Mock download service for testing."""

    def get_downloads(self) -> list:
        return []

    def add_download(self, download) -> None:
        pass

    def remove_downloads(self, indices: list) -> None:
        pass

    def clear_downloads(self) -> None:
        pass

    def start_download(self, download, options=None) -> None:
        pass

    def pause_download(self, download) -> None:
        pass

    def cancel_download(self, download) -> None:
        pass

    def has_downloads(self) -> bool:
        return False


class MockFileService(IFileService):
    """Mock file service for testing."""

    def clean_filename(self, filename: str) -> str:
        return filename

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        return f"{base_name}.{extension}"

    def ensure_directory(self, directory: str) -> bool:
        return True

    def get_file_size(self, file_path: str) -> int:
        return 1024

    def delete_file(self, file_path: str) -> bool:
        return True


class MockCookieHandler(ICookieHandler):
    """Mock cookie handler for testing."""

    def get_cookies(self) -> str:
        return "/mock/cookies.txt"

    def save_cookies(self, cookie_path: str) -> bool:
        return True

    def validate_cookies(self, cookie_path: str) -> bool:
        return True

    def clear_cookies(self) -> bool:
        return True

    def is_ready(self) -> bool:
        return True


class MockMetadataService(IMetadataService):
    """Mock metadata service for testing."""

    def fetch_metadata(self, url: str) -> object:
        return None


class MockNetworkChecker(INetworkChecker):
    """Mock network checker for testing."""

    def check_internet_connection(self) -> tuple[bool, str]:
        return True, "Connected"

    def check_service_connection(self, service_type: str) -> tuple[bool, str]:
        return True, f"{service_type} connected"

    def check_all_services(self) -> dict:
        return {"youtube": (True, ""), "twitter": (True, ""), "instagram": (True, "")}

    def is_service_connected(self, service_type: str) -> bool:
        return True


class MockAutoCookieManager(IAutoCookieManager):
    """Mock auto cookie manager for testing."""

    def initialize(self):
        from src.core.models import AuthState, CookieState

        return AuthState(
            service_type="youtube",
            cookie_state=CookieState.UNAVAILABLE,
            is_authenticated=False,
            auth_method=None,
        )

    def is_ready(self) -> bool:
        return False

    def get_cookies(self) -> str:
        return "/mock/autocookies.txt"


class MockUIState(IUIState):
    """Mock UI state for testing."""

    def set_download_directory(self, directory: str) -> None:
        pass

    def get_download_directory(self) -> str:
        return "~/Downloads"


class MockMessageQueue(IMessageQueue):
    """Mock message queue for testing."""

    def add_message(self, message) -> None:
        pass


class MockServiceFactory(IServiceFactory):
    """Mock service factory for testing."""

    def create_downloader(self, service_type: str):
        return None

    def get_supported_services(self) -> list:
        return ["youtube", "twitter", "instagram", "pinterest", "soundcloud"]


class TestApplicationOrchestrator:
    """Test ApplicationOrchestrator with proper dependency injection."""

    @patch('customtkinter.CTk')
    def test_orchestrator_instantiation(self, mock_ctk):
        """Test orchestrator can be instantiated with root window."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        assert orchestrator.root is mock_root
        assert orchestrator.container is not None
        assert orchestrator.event_coordinator is not None
        assert orchestrator.ui_state is not None

    @patch('customtkinter.CTk')
    def test_orchestrator_dependency_registration(self, mock_ctk):
        """Test that orchestrator registers all necessary dependencies."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Check that core interfaces are registered
        assert container.has(IErrorHandler)
        assert container.has(IDownloadHandler)
        assert container.has(IDownloadService)
        assert container.has(IFileService)
        assert container.has(ICookieHandler)
        assert container.has(IMetadataService)
        assert container.has(INetworkChecker)
        assert container.has(IAutoCookieManager)
        assert container.has(IServiceFactory)
        assert container.has(IUIState)

    @patch('customtkinter.CTk')
    def test_orchestrator_dependency_resolution(self, mock_ctk):
        """Test that orchestrator can resolve all dependencies."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Should be able to resolve all dependencies
        error_handler = container.get(IErrorHandler)
        download_handler = container.get(IDownloadHandler)
        download_service = container.get(IDownloadService)
        file_service = container.get(IFileService)
        cookie_handler = container.get(ICookieHandler)
        metadata_service = container.get(IMetadataService)
        network_checker = container.get(INetworkChecker)
        auto_cookie_manager = container.get(IAutoCookieManager)
        service_factory = container.get(IServiceFactory)
        ui_state = container.get(IUIState)

        # Verify we got the right types
        assert isinstance(error_handler, IErrorHandler)
        assert isinstance(download_handler, IDownloadHandler)
        assert isinstance(download_service, IDownloadService)
        assert isinstance(file_service, IFileService)
        assert isinstance(cookie_handler, ICookieHandler)
        assert isinstance(metadata_service, IMetadataService)
        assert isinstance(network_checker, INetworkChecker)
        assert isinstance(auto_cookie_manager, IAutoCookieManager)
        assert isinstance(service_factory, IServiceFactory)
        assert isinstance(ui_state, IUIState)

    @patch('customtkinter.CTk')
    def test_orchestrator_singleton_lifetimes(self, mock_ctk):
        """Test that orchestrator uses appropriate lifetimes."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Services should be singletons
        ui_state1 = container.get(IUIState)
        ui_state2 = container.get(IUIState)
        assert ui_state1 is ui_state2

        error_handler1 = container.get(IErrorHandler)
        error_handler2 = container.get(IErrorHandler)
        assert error_handler1 is error_handler2

    @patch('customtkinter.CTk')
    def test_orchestrator_set_ui_components(self, mock_ctk):
        """Test setting UI components on orchestrator."""
        mock_root = MagicMock()
        mock_url_entry = MagicMock()
        mock_download_list = MagicMock()
        mock_action_buttons = MagicMock()
        mock_status_bar = MagicMock()
        mock_progress_bar = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        orchestrator.set_ui_components(
            url_entry=mock_url_entry,
            download_list=mock_download_list,
            action_buttons=mock_action_buttons,
            status_bar=mock_status_bar,
            progress_bar=mock_progress_bar,
        )

        # Verify components were set (this would be tested more thoroughly
        # with actual implementation details)
        # For now, just verify it doesn't crash
        assert orchestrator.ui_components is not None

    @patch('customtkinter.CTk')
    def test_orchestrator_event_coordinator_creation(self, mock_ctk):
        """Test that orchestrator properly creates event coordinator."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        # Event coordinator should be created and have proper dependencies
        event_coordinator = orchestrator.event_coordinator
        assert event_coordinator is not None

        # Should have the same root
        assert event_coordinator.root is mock_root

    @patch('customtkinter.CTk')
    def test_orchestrator_ui_state_creation(self, mock_ctk):
        """Test that orchestrator creates UI state properly."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        ui_state = orchestrator.ui_state
        assert isinstance(ui_state, IUIState)
        assert ui_state.get_download_directory() == "~/Downloads"

    @patch('customtkinter.CTk')
    def test_orchestrator_auto_cookie_manager_property(self, mock_ctk):
        """Test auto cookie manager property."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        auto_cookie_manager = orchestrator.auto_cookie_manager
        assert isinstance(auto_cookie_manager, IAutoCookieManager)

    @patch('customtkinter.CTk')
    def test_orchestrator_error_handler_property(self, mock_ctk):
        """Test error handler property."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        error_handler = orchestrator.error_handler
        assert isinstance(error_handler, IErrorHandler)

    @patch('customtkinter.CTk')
    def test_orchestrator_connectivity_check(self, mock_ctk):
        """Test connectivity check functionality."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        # Should not raise any exceptions
        orchestrator.check_connectivity()

    @patch('customtkinter.CTk')
    def test_orchestrator_lazy_imports(self, mock_ctk):
        """Test that orchestrator uses lazy imports properly."""
        mock_root = MagicMock()

        # This should work without any import errors
        orchestrator = ApplicationOrchestrator(mock_root)

        # The fact that we got here means lazy imports worked
        assert orchestrator is not None


class TestOrchestratorIntegration:
    """Integration tests for orchestrator with the rest of the system."""

    @patch('customtkinter.CTk')
    def test_orchestrator_with_real_services(self, mock_ctk):
        """Test orchestrator with real service implementations."""
        from src.services.downloads import DownloadService
        from src.services.file import FileService
        from src.services.youtube.cookie_detector import CookieDetector
        from src.handlers.network_checker import NetworkChecker
        from src.handlers.download_handler import DownloadHandler
        from src.coordinators.error_handler import ErrorHandler

        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Override some services with real implementations
        container.register_singleton(IDownloadService, DownloadService)
        container.register_singleton(IFileService, FileService)
        container.register_singleton(INetworkChecker, NetworkChecker)
        container.register_singleton(IDownloadHandler, DownloadHandler)
        container.register_singleton(IErrorHandler, ErrorHandler)

        # Should be able to resolve real services
        download_service = container.get(IDownloadService)
        file_service = container.get(IFileService)
        network_checker = container.get(INetworkChecker)
        download_handler = container.get(IDownloadHandler)
        error_handler = container.get(IErrorHandler)

        assert isinstance(download_service, DownloadService)
        assert isinstance(file_service, FileService)
        assert isinstance(network_checker, NetworkChecker)
        assert isinstance(download_handler, DownloadHandler)
        assert isinstance(error_handler, ErrorHandler)

    @patch('customtkinter.CTk')
    def test_orchestrator_service_factory_integration(self, mock_ctk):
        """Test service factory integration with orchestrator."""
        from src.services.downloads import ServiceFactory

        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Override with real service factory
        container.register_singleton(IServiceFactory, ServiceFactory)

        service_factory = container.get(IServiceFactory)
        assert isinstance(service_factory, ServiceFactory)

        # Should be able to get supported services
        supported_services = service_factory.get_supported_services()
        assert isinstance(supported_services, list)
        assert len(supported_services) > 0

    @patch('customtkinter.CTk')
    def test_orchestrator_container_validation(self, mock_ctk):
        """Test that orchestrator's container passes validation."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Should not raise any exceptions
        container.validate_dependencies()

    @patch('customtkinter.CTk')
    def test_orchestrator_circular_dependency_prevention(self, mock_ctk):
        """Test that orchestrator prevents circular dependencies."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        # The orchestrator should initialize without circular dependency issues
        assert orchestrator.container is not None

        # All services should be resolvable
        try:
            orchestrator.container.get(IErrorHandler)
            orchestrator.container.get(IDownloadHandler)
            orchestrator.container.get(IDownloadService)
            orchestrator.container.get(IFileService)
            orchestrator.container.get(ICookieHandler)
            orchestrator.container.get(IMetadataService)
            orchestrator.container.get(INetworkChecker)
            orchestrator.container.get(IAutoCookieManager)
            orchestrator.container.get(IServiceFactory)
            orchestrator.container.get(IUIState)
        except Exception as e:
            pytest.fail(f"Service resolution failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__])