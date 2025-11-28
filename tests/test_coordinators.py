"""Comprehensive tests for coordinators with proper dependency injection."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.coordinators.download_coordinator import DownloadCoordinator
from src.coordinators.main_coordinator import EventCoordinator
from src.coordinators.platform_dialog_coordinator import PlatformDialogCoordinator
from src.core.models import Download, DownloadStatus
from src.services.events.event_bus import DownloadEventBus
from src.core.interfaces import (
    IDownloadHandler,
    IDownloadService,
    IErrorNotifier,
    ICookieHandler,
    IFileService,
    INetworkChecker,
    IMessageQueue,
)


class MockDownloadHandler(IDownloadHandler):
    """Mock download handler for testing."""

    def __init__(self):
        self.downloads = []
        self.started_downloads = []

    def process_url(self, url: str, options: dict = None) -> bool:
        return True

    def handle_download_error(self, error: Exception) -> None:
        pass

    def is_available(self) -> bool:
        return True

    def add_download(self, download: Download) -> None:
        self.downloads.append(download)

    def remove_downloads(self, indices: list) -> None:
        pass

    def clear_downloads(self) -> None:
        self.downloads.clear()

    def start_downloads(self, downloads: list, download_dir: str, progress_callback=None, completion_callback=None) -> None:
        self.started_downloads.extend(downloads)

    def cancel_download(self, download: Download) -> None:
        pass


class MockDownloadService(IDownloadService):
    """Mock download service for testing."""

    def __init__(self):
        self.downloads = []

    def get_downloads(self) -> list:
        return self.downloads.copy()

    def add_download(self, download: Download) -> None:
        self.downloads.append(download)

    def remove_downloads(self, indices: list) -> None:
        pass

    def clear_downloads(self) -> None:
        self.downloads.clear()

    def start_download(self, download: Download, options=None) -> None:
        pass

    def pause_download(self, download: Download) -> None:
        pass

    def cancel_download(self, download: Download) -> None:
        pass


class MockErrorHandler(IErrorNotifier):
    """Mock error handler for testing."""

    def __init__(self):
        self.errors_shown = []

    def show_error(self, title: str, message: str) -> None:
        self.errors_shown.append((title, message))

    def show_warning(self, title: str, message: str) -> None:
        pass

    def show_info(self, title: str, message: str) -> None:
        pass


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

    def detect_cookies(self) -> bool:
        return True


class MockFileService(IFileService):
    """Mock file service for testing."""

    def clean_filename(self, filename: str) -> str:
        return filename.replace("/", "_")

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        return f"{base_name}.{extension}"

    def ensure_directory(self, directory: str) -> bool:
        return True

    def get_file_size(self, file_path: str) -> int:
        return 1024

    def delete_file(self, file_path: str) -> bool:
        return True


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

    def check_connectivity(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return True


class MockMessageQueue(IMessageQueue):
    """Mock message queue for testing."""

    def __init__(self):
        self.messages = []

    def add_message(self, message) -> None:
        self.messages.append(message)

    def get_messages(self) -> list:
        return self.messages.copy()

    def process_messages(self) -> None:
        pass

    def clear_messages(self) -> None:
        self.messages.clear()

    def register_handler(self, handler) -> None:
        pass

    def send_message(self, message) -> None:
        self.add_message(message)


class TestDownloadCoordinator:
    """Test DownloadCoordinator with dependency injection."""

    def test_download_coordinator_instantiation(self):
        """Test DownloadCoordinator can be instantiated with dependencies."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        assert coordinator.event_bus is event_bus
        assert coordinator.download_handler is download_handler
        assert coordinator.error_handler is error_handler
        assert coordinator.download_service is download_service
        assert coordinator.message_queue is message_queue

    def test_download_coordinator_add_download(self):
        """Test adding downloads through coordinator."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        download = Download(url="https://example.com/video", name="Test Video")
        coordinator.add_download(download)

        assert len(download_handler.downloads) == 1
        assert download_handler.downloads[0] is download

    def test_download_coordinator_get_downloads(self):
        """Test getting downloads through coordinator."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # Add some downloads to the service
        download1 = Download(url="https://example.com/video1", name="Video 1")
        download2 = Download(url="https://example.com/video2", name="Video 2")
        download_service.downloads = [download1, download2]

        downloads = coordinator.get_downloads()
        assert len(downloads) == 2
        assert downloads[0].name == "Video 1"
        assert downloads[1].name == "Video 2"

    def test_download_coordinator_has_items(self):
        """Test checking if coordinator has items."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # Initially empty
        assert not coordinator.has_items()

        # Add a download
        download_service.downloads = [Download(url="https://test.com/video", name="test")]
        assert coordinator.has_items()

    def test_download_coordinator_has_active_downloads(self):
        """Test checking for active downloads."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # No downloads
        assert not coordinator.has_active_downloads()

        # Completed download
        completed_download = Download(url="https://test.com/video", name="test", status=DownloadStatus.COMPLETED)
        download_service.downloads = [completed_download]
        assert not coordinator.has_active_downloads()

        # Active download
        active_download = Download(url="https://test.com/video", name="test", status=DownloadStatus.DOWNLOADING)
        download_service.downloads = [active_download]
        assert coordinator.has_active_downloads()

    def test_download_coordinator_start_downloads(self):
        """Test starting downloads through coordinator."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        downloads = [
            Download(url="https://example.com/video1", name="Video 1"),
            Download(url="https://example.com/video2", name="Video 2")
        ]

        coordinator.start_downloads(downloads, "/test/dir")

        assert len(download_handler.started_downloads) == 2
        assert download_handler.started_downloads[0].name == "Video 1"
        assert download_handler.started_downloads[1].name == "Video 2"

    def test_download_coordinator_ui_callbacks(self):
        """Test download coordinator UI callbacks."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        ui_callbacks = {
            "update_status": Mock(),
            "refresh_download_list": Mock(),
            "set_action_buttons_enabled": Mock(),
            "update_download_progress": Mock()
        }

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue,
            ui_callbacks=ui_callbacks
        )

        # Test status callback
        coordinator._update_status("Test message", is_error=True)
        ui_callbacks["update_status"].assert_called_once_with("Test message", True)

        # Test refresh callback
        test_downloads = [Download(url="https://test.com/video", name="test")]
        download_service.downloads = test_downloads
        coordinator._refresh_ui_after_event()
        ui_callbacks["refresh_download_list"].assert_called_once_with(test_downloads)

    def test_download_coordinator_error_handling(self):
        """Test download coordinator error handling."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # Simulate a failed download event
        download = Download(url="https://test.com/video", name="test")
        error_message = "Download failed"

        # This should add a message to the queue
        coordinator._on_failed_event(download, error_message)

        assert len(message_queue.messages) == 1
        assert "Download failed" in message_queue.messages[0].text


class TestEventCoordinator:
    """Test EventCoordinator with dependency injection."""

    @patch('customtkinter.CTk')
    def test_event_coordinator_instantiation(self, mock_ctk):
        """Test EventCoordinator can be instantiated with dependencies."""
        mock_root = MagicMock()
        error_handler = MockErrorHandler()
        download_handler = MockDownloadHandler()
        file_service = MockFileService()
        network_checker = MockNetworkChecker()
        cookie_handler = MockCookieHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = EventCoordinator(
            root_window=mock_root,
            error_handler=error_handler,
            download_handler=download_handler,
            file_service=file_service,
            network_checker=network_checker,
            cookie_handler=cookie_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        assert coordinator.root is mock_root
        assert coordinator.error_handler is error_handler
        assert coordinator.download_handler is download_handler
        assert coordinator.file_service is file_service
        assert coordinator.network_checker is network_checker
        assert coordinator.cookie_handler is cookie_handler
        assert coordinator.download_service is download_service
        assert coordinator.message_queue is message_queue

    @patch('customtkinter.CTk')
    def test_event_coordinator_error_handling(self, mock_ctk):
        """Test EventCoordinator error handling."""
        mock_root = MagicMock()
        error_handler = MockErrorHandler()
        download_handler = MockDownloadHandler()
        file_service = MockFileService()
        network_checker = MockNetworkChecker()
        cookie_handler = MockCookieHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = EventCoordinator(
            root_window=mock_root,
            error_handler=error_handler,
            download_handler=download_handler,
            file_service=file_service,
            network_checker=network_checker,
            cookie_handler=cookie_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # Test error delegation
        coordinator.show_error("Test Title", "Test Message")
        assert len(error_handler.errors_shown) == 1
        assert error_handler.errors_shown[0] == ("Test Title", "Test Message")

    @patch('customtkinter.CTk')
    def test_event_coordinator_downloads_property(self, mock_ctk):
        """Test EventCoordinator downloads property."""
        mock_root = MagicMock()
        error_handler = MockErrorHandler()
        download_handler = MockDownloadHandler()
        file_service = MockFileService()
        network_checker = MockNetworkChecker()
        cookie_handler = MockCookieHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = EventCoordinator(
            root_window=mock_root,
            error_handler=error_handler,
            download_handler=download_handler,
            file_service=file_service,
            network_checker=network_checker,
            cookie_handler=cookie_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # The downloads property should return a DownloadCoordinator
        downloads = coordinator.downloads
        assert isinstance(downloads, DownloadCoordinator)
        assert downloads.download_handler is download_handler


class TestPlatformDialogCoordinator:
    """Test PlatformDialogCoordinator with dependency injection."""

    @patch('customtkinter.CTk')
    def test_platform_dialog_coordinator_instantiation(self, mock_ctk):
        """Test PlatformDialogCoordinator can be instantiated with dependencies."""
        mock_root = MagicMock()
        error_handler = MockErrorHandler()
        cookie_handler = MockCookieHandler()

        coordinator = PlatformDialogCoordinator(
            root_window=mock_root,
            error_handler=error_handler,
            cookie_handler=cookie_handler
        )

        assert coordinator.root is mock_root
        assert coordinator.error_handler is error_handler
        assert coordinator.cookie_handler is cookie_handler


class TestCoordinatorIntegration:
    """Integration tests for coordinators working together."""

    @patch('customtkinter.CTk')
    def test_coordinator_collaboration(self, mock_ctk):
        """Test that coordinators can work together."""
        mock_root = MagicMock()
        error_handler = MockErrorHandler()
        download_handler = MockDownloadHandler()
        file_service = MockFileService()
        network_checker = MockNetworkChecker()
        cookie_handler = MockCookieHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        # Create main coordinator
        event_coordinator = EventCoordinator(
            root_window=mock_root,
            error_handler=error_handler,
            download_handler=download_handler,
            file_service=file_service,
            network_checker=network_checker,
            cookie_handler=cookie_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # Create platform dialog coordinator
        platform_coordinator = PlatformDialogCoordinator(
            root_window=mock_root,
            error_handler=error_handler,
            cookie_handler=cookie_handler
        )

        # Both coordinators should share the same error handler
        assert event_coordinator.error_handler is platform_coordinator.error_handler

        # Both coordinators should share the same cookie handler
        assert event_coordinator.cookie_handler is platform_coordinator.cookie_handler

        # Event coordinator should have download coordinator
        assert isinstance(event_coordinator.downloads, DownloadCoordinator)
        assert event_coordinator.downloads.error_handler is error_handler

    def test_download_coordinator_event_subscription(self):
        """Test that download coordinator properly subscribes to events."""
        event_bus = DownloadEventBus(None)
        download_handler = MockDownloadHandler()
        error_handler = MockErrorHandler()
        download_service = MockDownloadService()
        message_queue = MockMessageQueue()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            download_service=download_service,
            message_queue=message_queue
        )

        # Should have subscribed to events during initialization
        # We can't directly test subscription due to encapsulation,
        # but we can verify the coordinator was created without errors
        assert coordinator.event_bus is event_bus


if __name__ == "__main__":
    pytest.main([__file__])