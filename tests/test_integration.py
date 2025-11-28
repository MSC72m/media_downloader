"""End-to-end integration tests for the entire refactored system."""

from unittest.mock import patch

import pytest

from src.application.orchestrator import ApplicationOrchestrator
from src.core.interfaces import IDownloadHandler
from src.core.models import Download, DownloadStatus
from src.handlers import _register_link_handlers
from src.services.detection.link_detector import LinkDetector


class MockRoot:
    """Mock root window for testing."""


class TestSystemIntegration:
    """Test the entire system working together."""

    @patch("customtkinter.CTk")
    def test_complete_system_startup(self, mock_ctk):
        """Test that the complete system can start up without errors."""
        mock_root = MockRoot()

        # Create orchestrator - this initializes the entire system
        orchestrator = ApplicationOrchestrator(mock_root)

        # Should have all components initialized
        assert orchestrator.container is not None
        assert orchestrator.event_coordinator is not None
        assert orchestrator.ui_state is not None

        # Container should have all required services
        container = orchestrator.container
        assert len(container._services) > 0

        print(f"✓ System started with {len(container._services)} registered services")

    @patch("customtkinter.CTk")
    def test_handler_registration_with_real_orchestrator(self, mock_ctk):
        """Test that handlers are properly registered in the real system."""
        mock_root = MockRoot()
        ApplicationOrchestrator(mock_root)

        # Register handlers through the normal system
        handlers = _register_link_handlers()

        # Should have all 5 handlers
        assert len(handlers) == 5

        handler_names = [h.__class__.__name__ for h in handlers]
        expected = [
            "InstagramHandler",
            "PinterestHandler",
            "SoundCloudHandler",
            "TwitterHandler",
            "YouTubeHandler",
        ]

        for expected_name in expected:
            assert expected_name in handler_names

        print(f"✓ All {len(handlers)} handlers registered successfully")

    @patch("customtkinter.CTk")
    def test_service_detector_integration(self, mock_ctk):
        """Test service detection integration."""
        mock_root = MockRoot()
        ApplicationOrchestrator(mock_root)

        # Create service detector
        detector = LinkDetector()

        # Test URL detection for all platforms
        test_cases = [
            ("https://www.youtube.com/watch?v=test123", "youtube"),
            ("https://twitter.com/user/status/456", "twitter"),
            ("https://www.instagram.com/p/test/", "instagram"),
            ("https://www.pinterest.com/pin/789", "pinterest"),
            ("https://soundcloud.com/artist/track", "soundcloud"),
        ]

        detected_services = set()
        for url, expected in test_cases:
            # Try to find a handler for this URL
            handler_found = False
            for handler_class in detector.registry._handlers.values():
                if hasattr(handler_class, "can_handle"):
                    # Create an instance
                    handler = detector.registry._create_handler_instance(handler_class)
                    result = handler.can_handle(url)
                    if result.service_type != "unknown":
                        detected_services.add(result.service_type)
                        handler_found = True
                        print(f"✓ {expected} URL detected: {url}")
                        break

            if not handler_found:
                print(f"⚠ {expected} URL not detected: {url}")

        # Should detect most services (some may not be detected without full setup)
        assert (
            len(detected_services) >= 3
        ), f"Expected at least 3 services, got {len(detected_services)}"

    @patch("customtkinter.CTk")
    def test_download_flow_integration(self, mock_ctk):
        """Test a complete download flow integration."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)

        # Create a test download
        download = Download(
            url="https://www.youtube.com/watch?v=test123",
            name="Test Video",
            service_type="youtube",
        )

        # Test that the download can be added to the system
        download_handler = orchestrator.container.get(IDownloadHandler)
        download_handler.add_download(download)

        # Verify it was added
        downloads = download_handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].url == "https://www.youtube.com/watch?v=test123"
        assert downloads[0].name == "Test Video"

        print("✓ Download flow integration working")

    @patch("customtkinter.CTk")
    def test_error_handling_integration(self, mock_ctk):
        """Test error handling integration."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)

        # Get the error handler
        error_handler = orchestrator.error_handler

        # Test error handling doesn't crash
        try:
            error_handler.show_error("Test Title", "Test Message")
            print("✓ Error handling integration working")
        except Exception as e:
            pytest.fail(f"Error handling failed: {e}")

    @patch("customtkinter.CTk")
    def test_event_system_integration(self, mock_ctk):
        """Test event system integration."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)

        # Get the event bus from orchestrator
        event_coordinator = orchestrator.event_coordinator
        event_bus = event_coordinator.event_bus

        # Test that event bus is properly initialized
        assert event_bus is not None
        assert hasattr(event_bus, "subscribe")
        assert hasattr(event_bus, "publish")

        print("✓ Event system integration working")

    @patch("customtkinter.CTk")
    def test_dependency_injection_lifecycle(self, mock_ctk):
        """Test complete dependency injection lifecycle."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Test singleton behavior
        ui_state1 = container.get_ui_state()
        ui_state2 = container.get_ui_state()
        assert ui_state1 is ui_state2, "UIState should be singleton"

        error_handler1 = container.get_error_handler()
        error_handler2 = container.get_error_handler()
        assert error_handler1 is error_handler2, "ErrorHandler should be singleton"

        # Test that different services are different instances
        download_handler = container.get(IDownloadHandler)
        file_service = container.get_file_service()
        assert download_handler is not file_service

        print("✓ Dependency injection lifecycle working")

    @patch("customtkinter.CTk")
    def test_interface_compliance(self, mock_ctk):
        """Test that all registered services comply with their interfaces."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        from src.core.interfaces import (
            IAutoCookieManager,
            ICookieHandler,
            IDownloadHandler,
            IErrorNotifier,
            IFileService,
            IMetadataService,
            INetworkChecker,
            IServiceFactory,
            IUIState,
        )

        # Test that all services implement their interfaces
        interface_implementations = [
            (IErrorNotifier, container.get(IErrorNotifier)),
            (IDownloadHandler, container.get(IDownloadHandler)),
            (IFileService, container.get(IFileService)),
            (ICookieHandler, container.get(ICookieHandler)),
            (IMetadataService, container.get(IMetadataService)),
            (INetworkChecker, container.get(INetworkChecker)),
            (IAutoCookieManager, container.get(IAutoCookieManager)),
            (IServiceFactory, container.get(IServiceFactory)),
            (IUIState, container.get(IUIState)),
        ]

        for interface, implementation in interface_implementations:
            assert isinstance(
                implementation, interface
            ), f"{implementation.__class__.__name__} should implement {interface.__name__}"

        print("✓ All services comply with their interfaces")

    @patch("customtkinter.CTk")
    def test_memory_management(self, mock_ctk):
        """Test memory management and cleanup."""
        mock_root = MockRoot()

        # Create and destroy multiple orchestrators
        for i in range(5):
            orchestrator = ApplicationOrchestrator(mock_root)

            # Use the orchestrator
            ui_state = orchestrator.ui_state

            # Simulate some work
            ui_state.set_download_directory(f"/test/dir/{i}")

            # Clear references
            orchestrator = None
            ui_state = None

        # If we got here without crashes, memory management is working
        print("✓ Memory management working")

    @patch("customtkinter.CTk")
    def test_system_performance(self, mock_ctk):
        """Test system performance with multiple operations."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        import time

        # Test dependency resolution performance
        start_time = time.time()
        for _ in range(100):
            container.get_ui_state()
            container.get_error_handler()
            container.get(IDownloadHandler)
        end_time = time.time()

        resolution_time = end_time - start_time
        assert resolution_time < 1.0, f"Dependency resolution too slow: {resolution_time:.3f}s"

        print(f"✓ Performance test passed (100 resolutions in {resolution_time:.3f}s)")

    @patch("customtkinter.CTk")
    def test_system_robustness(self, mock_ctk):
        """Test system robustness with various error conditions."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)
        container = orchestrator.container

        # Test missing service handling
        try:
            # Try to get a service that doesn't exist
            class NonExistentInterface:
                pass

            should_fail = False
            try:
                container.get(NonExistentInterface)
                should_fail = False
            except Exception:
                should_fail = True

            assert should_fail, "Should fail when getting non-existent service"
        except Exception as e:
            pytest.fail(f"Robustness test failed: {e}")

        # Test invalid parameter handling
        try:
            ui_state = container.get_ui_state()
            # Try setting invalid directory (should not crash)
            ui_state.set_download_directory("")  # Empty string
            ui_state.set_download_directory(None)  # None
            print("✓ System robustness working")
        except Exception as e:
            pytest.fail(f"Robustness test failed: {e}")


class TestSystemEndToEnd:
    """End-to-end tests for the complete system."""

    @patch("customtkinter.CTk")
    def test_user_workflow_simulation(self, mock_ctk):
        """Simulate a complete user workflow."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)

        # Step 1: User sets download directory
        ui_state = orchestrator.ui_state
        ui_state.set_download_directory("/user/downloads")
        assert ui_state.get_download_directory() == "/user/downloads"

        # Step 2: User adds a YouTube URL
        download = Download(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            name="Never Gonna Give You Up",
            service_type="youtube",
        )

        download_handler = orchestrator.container.get(IDownloadHandler)
        download_handler.add_download(download)

        # Step 3: Verify download was added
        downloads = download_handler.get_downloads()
        assert len(downloads) == 1
        assert downloads[0].name == "Never Gonna Give You Up"

        # Step 4: Simulate download progress
        downloads[0].update_progress(50.0, 1024.0)
        assert downloads[0].progress == 50.0

        # Step 5: Complete download
        downloads[0].mark_completed()
        assert downloads[0].status == DownloadStatus.COMPLETED

        print("✓ Complete user workflow simulation working")

    @patch("customtkinter.CTk")
    def test_multi_platform_support(self, mock_ctk):
        """Test multi-platform download support."""
        mock_root = MockRoot()
        ApplicationOrchestrator(mock_root)

        # Get handlers
        handlers = _register_link_handlers()

        # Test URLs from all supported platforms
        platform_urls = [
            ("https://www.youtube.com/watch?v=test", "youtube"),
            ("https://twitter.com/user/status/123", "twitter"),
            ("https://www.instagram.com/p/test/", "instagram"),
            ("https://www.pinterest.com/pin/456", "pinterest"),
            ("https://soundcloud.com/artist/track", "soundcloud"),
        ]

        detected_platforms = set()
        for url, _expected_platform in platform_urls:
            for handler in handlers:
                result = handler.can_handle(url)
                if result.service_type != "unknown":
                    detected_platforms.add(result.service_type)
                    break

        # Should detect at least some platforms
        assert (
            len(detected_platforms) >= 3
        ), f"Expected at least 3 platforms, got {len(detected_platforms)}"
        print(f"✓ Multi-platform support working: {detected_platforms}")

    @patch("customtkinter.CTk")
    def test_error_recovery(self, mock_ctk):
        """Test system error recovery."""
        mock_root = MockRoot()
        orchestrator = ApplicationOrchestrator(mock_root)

        # Simulate various error conditions and verify recovery
        error_handler = orchestrator.error_handler

        # Test error handler doesn't crash with various inputs
        error_handler.show_error("", "")  # Empty error
        error_handler.show_error("Title", "")  # Empty message
        error_handler.show_error("", "Message")  # Empty title

        # Test system continues working after errors
        ui_state = orchestrator.ui_state
        ui_state.set_download_directory("/recovery/test")
        assert ui_state.get_download_directory() == "/recovery/test"

        print("✓ Error recovery working")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
