"""Tests for the application orchestration system."""

from unittest.mock import MagicMock, patch

import pytest

from src.application.orchestrator import ApplicationOrchestrator
from src.core.interfaces import (
    IAutoCookieManager,
    ICookieHandler,
    IDownloadHandler,
    IErrorNotifier,
    IFileService,
    IMessageQueue,
    IMetadataService,
    INetworkChecker,
    IServiceFactory,
    IUIState,
)

class TestApplicationOrchestrator:
    """Test ApplicationOrchestrator with proper dependency injection."""

    @patch("customtkinter.CTk")
    def test_orchestrator_instantiation(self, mock_ctk):
        """Test orchestrator can be instantiated with root window."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        assert orchestrator.root is mock_root
        assert orchestrator.container is not None
        assert orchestrator.event_coordinator is not None
        assert orchestrator.ui_state is not None

    @patch("customtkinter.CTk")
    def test_orchestrator_dependency_registration(self, mock_ctk):
        """Test that orchestrator registers all necessary dependencies."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Check that core interfaces are registered
        assert container.has(IErrorNotifier)
        assert container.has(IDownloadHandler)
        assert container.has(IFileService)
        assert container.has(ICookieHandler)
        assert container.has(IMetadataService)
        assert container.has(INetworkChecker)
        assert container.has(IAutoCookieManager)
        assert container.has(IServiceFactory)
        assert container.has(IUIState)

    @patch("customtkinter.CTk")
    def test_orchestrator_dependency_resolution(self, mock_ctk):
        """Test that orchestrator can resolve all dependencies."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Should be able to resolve all dependencies
        error_handler = container.get(IErrorNotifier)
        download_handler = container.get(IDownloadHandler)
        file_service = container.get(IFileService)
        cookie_handler = container.get(ICookieHandler)
        metadata_service = container.get(IMetadataService)
        network_checker = container.get(INetworkChecker)
        auto_cookie_manager = container.get(IAutoCookieManager)
        service_factory = container.get(IServiceFactory)
        ui_state = container.get(IUIState)

        # Verify we got the right types
        assert isinstance(error_handler, IErrorNotifier)
        assert isinstance(download_handler, IDownloadHandler)
        assert isinstance(file_service, IFileService)
        assert isinstance(cookie_handler, ICookieHandler)
        # YouTubeMetadataService implements IYouTubeMetadataService interface
        assert hasattr(metadata_service, "fetch_metadata")
        assert hasattr(metadata_service, "get_available_subtitles")
        assert isinstance(network_checker, INetworkChecker)
        assert isinstance(auto_cookie_manager, IAutoCookieManager)
        assert isinstance(service_factory, IServiceFactory)
        assert isinstance(ui_state, IUIState)

    @patch("customtkinter.CTk")
    def test_orchestrator_singleton_lifetimes(self, mock_ctk):
        """Test that orchestrator uses appropriate lifetimes."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Services should be singletons
        ui_state1 = container.get(IUIState)
        ui_state2 = container.get(IUIState)
        assert ui_state1 is ui_state2

        error_handler1 = container.get(IErrorNotifier)
        error_handler2 = container.get(IErrorNotifier)
        assert error_handler1 is error_handler2

    @patch("customtkinter.CTk")
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

    @patch("customtkinter.CTk")
    def test_orchestrator_event_coordinator_creation(self, mock_ctk):
        """Test that orchestrator properly creates event coordinator."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        # Event coordinator should be created and have proper dependencies
        event_coordinator = orchestrator.event_coordinator
        assert event_coordinator is not None

        # Should have the same root
        assert event_coordinator.root is mock_root

    @patch("customtkinter.CTk")
    def test_orchestrator_ui_state_creation(self, mock_ctk):
        """Test that orchestrator creates UI state properly."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        ui_state = orchestrator.ui_state
        assert isinstance(ui_state, IUIState)
        # UIState has download_directory attribute, not get_download_directory method
        assert hasattr(ui_state, "download_directory")
        assert ui_state.download_directory is not None

    @patch("customtkinter.CTk")
    def test_orchestrator_auto_cookie_manager_property(self, mock_ctk):
        """Test auto cookie manager property."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        auto_cookie_manager = orchestrator.auto_cookie_manager
        assert isinstance(auto_cookie_manager, IAutoCookieManager)

    @patch("customtkinter.CTk")
    def test_orchestrator_error_handler_property(self, mock_ctk):
        """Test error handler property."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        error_handler = orchestrator.error_handler
        assert isinstance(error_handler, IErrorNotifier)

    @patch("customtkinter.CTk")
    def test_orchestrator_connectivity_check(self, mock_ctk):
        """Test connectivity check functionality."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        # Should not raise any exceptions
        orchestrator.check_connectivity()

    @patch("customtkinter.CTk")
    def test_orchestrator_lazy_imports(self, mock_ctk):
        """Test that orchestrator uses lazy imports properly."""
        mock_root = MagicMock()

        # This should work without any import errors
        orchestrator = ApplicationOrchestrator(mock_root)

        # The fact that we got here means lazy imports worked
        assert orchestrator is not None


class TestOrchestratorIntegration:
    """Integration tests for orchestrator with the rest of the system."""

    @patch("customtkinter.CTk")
    def test_orchestrator_with_real_services(self, mock_ctk):
        """Test orchestrator with real service implementations."""
        from src.coordinators.error_notifier import ErrorNotifier
        from src.handlers.download_handler import DownloadHandler
        from src.handlers.network_checker import NetworkChecker
        from src.services.file import FileService

        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Override some services with real implementations
        container.register_singleton(IFileService, FileService)
        container.register_singleton(INetworkChecker, NetworkChecker)
        container.register_singleton(IDownloadHandler, DownloadHandler)
        container.register_singleton(IErrorNotifier, ErrorNotifier)

        # Should be able to resolve real services
        file_service = container.get(IFileService)
        network_checker = container.get(INetworkChecker)
        download_handler = container.get(IDownloadHandler)
        error_handler = container.get(IErrorNotifier)

        assert isinstance(file_service, FileService)
        assert isinstance(network_checker, NetworkChecker)
        assert isinstance(download_handler, DownloadHandler)
        assert isinstance(error_handler, ErrorNotifier)

    @patch("customtkinter.CTk")
    def test_orchestrator_service_factory_integration(self, mock_ctk):
        """Test service factory integration with orchestrator."""
        from src.application.service_factory import ServiceFactory

        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Override with real service factory
        container.register_singleton(IServiceFactory, ServiceFactory)

        service_factory = container.get(IServiceFactory)
        assert isinstance(service_factory, ServiceFactory)

        # Should be able to create services
        assert hasattr(service_factory, "get_downloader")
        assert hasattr(service_factory, "detect_service_type")
        assert hasattr(service_factory, "get_cookie_manager")

    @patch("customtkinter.CTk")
    def test_orchestrator_container_validation(self, mock_ctk):
        """Test that orchestrator's container passes validation."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Should not raise any exceptions
        container.validate_dependencies()

    @patch("customtkinter.CTk")
    def test_orchestrator_circular_dependency_prevention(self, mock_ctk):
        """Test that orchestrator prevents circular dependencies."""
        mock_root = MagicMock()

        orchestrator = ApplicationOrchestrator(mock_root)

        # The orchestrator should initialize without circular dependency issues
        assert orchestrator.container is not None

        # All services should be resolvable
        try:
            orchestrator.container.get(IErrorNotifier)
            orchestrator.container.get(IDownloadHandler)
            orchestrator.container.get(IDownloadHandler)
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
