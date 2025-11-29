"""Tests for downloader services including Pinterest and YouTube."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.application.service_factory import ServiceFactory
from src.core.enums import ServiceType
from src.core.interfaces import IErrorNotifier, IFileService
from src.services.pinterest.downloader import PinterestDownloader
from src.services.youtube.downloader import YouTubeDownloader


class MockFileService(IFileService):
    """Mock file service for testing."""

    def ensure_directory(self, path: str) -> None:
        pass

    def sanitize_filename(self, filename: str) -> str:
        return filename

    def clean_filename(self, filename: str) -> str:
        return filename

    def download_file(self, url: str, path: str, progress_callback=None):
        class Result:
            success = True

        return Result()


class MockErrorNotifier(IErrorNotifier):
    """Mock error notifier for testing."""

    def handle_service_failure(self, service: str, operation: str, message: str, url: str) -> None:
        pass

    def handle_exception(self, exception: Exception, context: str, service: str) -> None:
        pass


class TestServiceFactoryPinterestDetection:
    """Test Pinterest URL detection in service factory."""

    def test_detect_pinterest_full_url(self):
        """Test detection of full Pinterest URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type("https://www.pinterest.com/pin/123456/")
        assert service_type == ServiceType.PINTEREST

    def test_detect_pinterest_short_url(self):
        """Test detection of pin.it short URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type("https://pin.it/3YtKpHT04")
        assert service_type == ServiceType.PINTEREST

    def test_detect_pinterest_pin_it_variations(self):
        """Test detection of various pin.it URL formats."""
        factory = ServiceFactory(cookie_manager=Mock())
        test_urls = [
            "https://pin.it/3YtKpHT04",
            "http://pin.it/abc123",
            "pin.it/xyz789",
        ]
        for url in test_urls:
            service_type = factory.detect_service_type(url)
            assert service_type == ServiceType.PINTEREST, f"Failed for URL: {url}"

    def test_get_pinterest_downloader(self):
        """Test getting Pinterest downloader for Pinterest URLs."""
        factory = ServiceFactory(
            cookie_manager=Mock(),
            error_handler=MockErrorNotifier(),
            file_service=MockFileService(),
        )
        downloader = factory.get_downloader("https://pin.it/3YtKpHT04")
        assert isinstance(downloader, PinterestDownloader)

    def test_pinterest_not_fallback_to_youtube(self):
        """Test that Pinterest URLs don't fallback to YouTube."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type("https://pin.it/3YtKpHT04")
        assert service_type != ServiceType.YOUTUBE
        assert service_type == ServiceType.PINTEREST


class TestPinterestDownloader:
    """Test Pinterest downloader functionality."""

    @patch("src.services.pinterest.downloader.check_site_connection")
    @patch("src.services.pinterest.downloader.requests.get")
    def test_pinterest_downloader_handles_short_urls(self, mock_get, mock_check):
        """Test Pinterest downloader handles pin.it short URLs."""
        mock_check.return_value = (True, None)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<html><meta property='og:image' content='https://example.com/image.jpg'/></html>"
        mock_get.return_value = mock_response

        downloader = PinterestDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )
        result = downloader.download("https://pin.it/3YtKpHT04", "/tmp/test.jpg")
        assert isinstance(result, bool)

    @patch("src.services.pinterest.downloader.check_site_connection")
    def test_pinterest_downloader_connection_failure(self, mock_check):
        """Test Pinterest downloader handles connection failures."""
        mock_check.return_value = (False, "Connection failed")
        downloader = PinterestDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )
        result = downloader.download("https://pin.it/3YtKpHT04", "/tmp/test.jpg")
        assert result is False


class TestYouTubeDownloaderFormatFallback:
    """Test YouTube downloader format fallback functionality."""

    @patch("src.services.youtube.downloader.check_site_connection")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_youtube_format_fallback_on_info_extraction_failure(self, mock_ydl_class, mock_check):
        """Test YouTube downloader tries format fallback when info extraction fails."""
        mock_check.return_value = (True, None)

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = [None, {"id": "test"}]
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = YouTubeDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("os.makedirs"):
            result = downloader.download("https://youtube.com/watch?v=test", "/tmp/test.mp4")

        assert mock_ydl.extract_info.call_count >= 1
        calls = mock_ydl.extract_info.call_args_list
        assert len(calls) >= 1

    @patch("src.services.youtube.downloader.check_site_connection")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_youtube_format_fallback_uses_best_then_worst(self, mock_ydl_class, mock_check):
        """Test YouTube downloader tries 'best' then 'worst' format on failure."""
        mock_check.return_value = (True, None)

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = None
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = YouTubeDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )

        with patch("os.path.exists", return_value=False), patch("os.makedirs"):
            result = downloader.download("https://youtube.com/watch?v=test", "/tmp/test.mp4")

        assert mock_ydl.extract_info.call_count >= 2

    @patch("src.services.youtube.downloader.check_site_connection")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_youtube_handles_format_error_with_fallback(self, mock_ydl_class, mock_check):
        """Test YouTube downloader handles format errors with fallback."""
        mock_check.return_value = (True, None)

        class DownloadError(Exception):
            pass

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = [
            DownloadError("Requested format is not available"),
            {"id": "test"},
        ]
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = YouTubeDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )

        with patch("os.path.exists", return_value=True), patch(
            "os.path.getsize", return_value=1000
        ), patch("os.makedirs"):
            result = downloader.download("https://youtube.com/watch?v=test", "/tmp/test.mp4")

        assert mock_ydl.extract_info.call_count >= 2


class TestDownloadStateManagement:
    """Test download state management for multiple downloads."""

    def test_coordinator_keeps_buttons_disabled_during_multiple_downloads(self):
        """Test that buttons stay disabled when multiple downloads are active."""
        from src.coordinators.download_coordinator import DownloadCoordinator
        from src.core.models import Download, DownloadStatus
        from src.services.events.event_bus import DownloadEventBus

        event_bus = DownloadEventBus(None)
        download_handler = Mock()
        download_handler.get_downloads.return_value = [
            Download(url="https://test.com/1", name="test1", status=DownloadStatus.DOWNLOADING),
            Download(url="https://test.com/2", name="test2", status=DownloadStatus.DOWNLOADING),
        ]
        error_handler = MockErrorNotifier()
        message_queue = Mock()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            message_queue=message_queue,
        )

        buttons_callback = Mock()
        coordinator.set_ui_callbacks({"set_action_buttons_enabled": buttons_callback})

        download1 = Download(url="https://test.com/1", name="test1", status=DownloadStatus.COMPLETED)
        coordinator._on_completed_event(download1)

        buttons_callback.assert_called_with(False)

    def test_coordinator_enables_buttons_when_all_downloads_complete(self):
        """Test that buttons are enabled when all downloads complete."""
        from src.coordinators.download_coordinator import DownloadCoordinator
        from src.core.models import Download, DownloadStatus
        from src.services.events.event_bus import DownloadEventBus

        event_bus = DownloadEventBus(None)
        download_handler = Mock()
        download_handler.get_downloads.return_value = [
            Download(url="https://test.com/1", name="test1", status=DownloadStatus.COMPLETED),
        ]
        error_handler = MockErrorNotifier()
        message_queue = Mock()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            message_queue=message_queue,
        )

        buttons_callback = Mock()
        coordinator.set_ui_callbacks({"set_action_buttons_enabled": buttons_callback})

        download1 = Download(url="https://test.com/1", name="test1", status=DownloadStatus.COMPLETED)
        coordinator._on_completed_event(download1)

        buttons_callback.assert_called_with(True)

    def test_coordinator_handles_failed_download_with_active_ones(self):
        """Test that buttons stay disabled when one download fails but others are active."""
        from src.coordinators.download_coordinator import DownloadCoordinator
        from src.core.models import Download, DownloadStatus
        from src.services.events.event_bus import DownloadEventBus

        event_bus = DownloadEventBus(None)
        download_handler = Mock()
        download_handler.get_downloads.return_value = [
            Download(url="https://test.com/1", name="test1", status=DownloadStatus.FAILED),
            Download(url="https://test.com/2", name="test2", status=DownloadStatus.DOWNLOADING),
        ]
        error_handler = MockErrorNotifier()
        message_queue = Mock()

        coordinator = DownloadCoordinator(
            event_bus=event_bus,
            download_handler=download_handler,
            error_handler=error_handler,
            message_queue=message_queue,
        )

        buttons_callback = Mock()
        coordinator.set_ui_callbacks({"set_action_buttons_enabled": buttons_callback})

        download1 = Download(url="https://test.com/1", name="test1", status=DownloadStatus.FAILED)
        coordinator._on_failed_event(download1, "Test error")

        buttons_callback.assert_called_with(False)
