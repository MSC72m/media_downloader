"""Comprehensive unit tests for TikTok downloader and handler."""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch
import re

import pytest

from src.core.config import AppConfig
from src.core.enums import ServiceType
from src.core.interfaces import IErrorNotifier, IFileService, IMessageQueue
from src.handlers.tiktok_handler import TikTokHandler
from src.services.tiktok.downloader import TikTokDownloader


class MockFileService(IFileService):
    """Mock file service for testing."""

    def ensure_directory(self, path: str) -> bool:
        return True

    def sanitize_filename(self, filename: str) -> str:
        return filename

    def clean_filename(self, filename: str) -> str:
        return filename

    def download_file(self, url: str, path: str, progress_callback=None):
        class Result:
            success = True

        return Result()

    def get_unique_filename(self, path: str, extension: str = "") -> str:
        return path + extension


class MockErrorNotifier(IErrorNotifier):
    """Mock error notifier for testing."""

    def handle_service_failure(
        self,
        service: str,
        operation: str,
        error_message: str,
        url: str,
        exception: Exception | None = None,
    ) -> None:
        pass

    def handle_exception(
        self, exception: Exception, context: str, service: str, url: str = ""
    ) -> None:
        pass

    def show_error(self, title: str, message: str) -> None:
        pass

    def show_warning(self, title: str, message: str) -> None:
        pass


class MockMessageQueue(IMessageQueue):
    """Mock message queue for testing."""

    def post(self, message: str) -> None:
        pass

    def add_message(self, message: str) -> None:
        pass

    def send_message(self, message: str) -> None:
        pass

    def clear(self) -> None:
        pass

    def get_messages(self) -> list[str]:
        return []


class TestTikTokDownloader:
    """Test TikTok downloader functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.downloader = TikTokDownloader(
            error_handler=MockErrorNotifier(),
            file_service=MockFileService(),
        )

    def test_initialization_with_default_config(self):
        """Test TikTok downloader initialization with default config."""
        assert self.downloader.default_timeout > 0
        assert self.downloader.max_retries > 0

    def test_initialization_with_custom_config(self):
        """Test TikTok downloader initialization with custom config."""
        custom_config = Mock()
        custom_config.tiktok.default_timeout = 60
        custom_config.tiktok.max_retries = 5

        downloader = TikTokDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=custom_config
        )

        assert downloader.default_timeout == 60
        assert downloader.max_retries == 5

    def test_get_ytdl_options(self):
        """Test yt-dlp options generation."""
        options = self.downloader._get_ytdl_options()

        assert options["format"] == "best"
        assert options["quiet"] is True
        assert options["no_warnings"] is True
        assert options["ignoreerrors"] is True
        assert "extractor_args" in options
        assert "tiktok" in options["extractor_args"]
        assert options["extractor_args"]["tiktok"]["enable_download"] is True
        assert options["extractor_args"]["tiktok"]["enable_music"] is True
        assert options["extractor_args"]["tiktok"]["download_thumbnail"] is True

    def test_validate_download_inputs_valid(self):
        """Test validation with valid inputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            assert (
                self.downloader._validate_download_inputs(
                    "https://tiktok.com/@user/video/123", save_path
                )
                is True
            )

    def test_validate_download_inputs_no_url(self):
        """Test validation with no URL."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            assert self.downloader._validate_download_inputs("", save_path) is False

    def test_validate_download_inputs_nonexistent_directory(self):
        """Test validation with non-existent save directory."""
        nonexistent_path = "/nonexistent/directory/test_video"
        assert (
            self.downloader._validate_download_inputs(
                "https://tiktok.com/@user/video/123", nonexistent_path
            )
            is False
        )

    @patch("src.services.tiktok.downloader.yt_dlp.YoutubeDL")
    def test_perform_download_success(self, mock_ydl_class):
        """Test successful download."""
        mock_ydl = MagicMock()
        mock_info = {"id": "test123", "title": "Test TikTok Video"}
        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            result = self.downloader._perform_download(
                "https://tiktok.com/@user/video/123", save_path, None
            )

            assert result is True
            mock_ydl.extract_info.assert_called_once_with(
                "https://tiktok.com/@user/video/123", download=True
            )

    @patch("src.services.tiktok.downloader.yt_dlp.YoutubeDL")
    def test_perform_download_extraction_failure(self, mock_ydl_class):
        """Test download failure due to info extraction failure."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = None
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            result = self.downloader._perform_download(
                "https://tiktok.com/@user/video/123", save_path, None
            )

            assert result is False

    @patch("src.services.tiktok.downloader.yt_dlp.YoutubeDL")
    def test_perform_download_exception(self, mock_ydl_class):
        """Test download failure due to exception."""
        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = Exception("Download error")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            result = self.downloader._perform_download(
                "https://tiktok.com/@user/video/123", save_path, None
            )

            assert result is False

    @patch("src.services.tiktok.downloader.yt_dlp.YoutubeDL")
    def test_download_full_success(self, mock_ydl_class):
        """Test full download process with success."""
        mock_ydl = MagicMock()
        mock_info = {"id": "test123", "title": "Test TikTok Video"}
        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            result = self.downloader.download("https://tiktok.com/@user/video/123", save_path)

            assert result is True

    def test_download_invalid_inputs(self):
        """Test download with invalid inputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_video")
            result = self.downloader.download("", save_path)
            assert result is False

    def test_create_progress_hook_without_callback(self):
        """Test progress hook creation without callback."""
        hook = self.downloader._create_progress_hook(None)

        # Should not raise exception when called
        hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})

    def test_create_progress_hook_with_callback(self):
        """Test progress hook creation with callback."""
        callback_calls = []

        def progress_callback(progress, speed):
            callback_calls.append((progress, speed))

        hook = self.downloader._create_progress_hook(progress_callback)

        # Test downloading status
        hook(
            {
                "status": "downloading",
                "downloaded_bytes": 50,
                "total_bytes": 100,
                "speed": 1024 * 1024,  # 1 MB/s
            }
        )

        assert len(callback_calls) == 1
        progress, speed = callback_calls[0]
        assert progress == 50.0
        assert speed > 0

    def test_create_progress_hook_finished_status(self):
        """Test progress hook with finished status."""
        callback_calls = []

        def progress_callback(progress, speed):
            callback_calls.append((progress, speed))

        hook = self.downloader._create_progress_hook(progress_callback)
        hook({"status": "finished"})

        assert len(callback_calls) == 1
        progress, speed = callback_calls[0]
        assert progress == 100.0
        assert speed == 0.0

    def test_create_progress_handle_callback_exception(self):
        """Test progress hook handles callback exceptions gracefully."""

        def failing_callback(progress, speed):
            raise Exception("Callback error")

        hook = self.downloader._create_progress_hook(failing_callback)

        # Should not raise exception
        hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100})


class TestTikTokHandler:
    """Test TikTok handler functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = AppConfig()
        self.handler = TikTokHandler(
            message_queue=MockMessageQueue(), error_handler=MockErrorNotifier(), config=self.config
        )

    def test_get_patterns(self):
        """Test getting URL patterns for TikTok handler."""
        patterns = self.handler.get_patterns()
        assert isinstance(patterns, list)

    def test_extract_metadata(self):
        """Test TikTok metadata extraction."""
        url = "https://www.tiktok.com/@user/video/123456789"
        metadata = self.handler._extract_metadata(url)

        assert metadata["type"] == "video"
        assert metadata["video_id"] == "123456789"

    def test_get_metadata(self):
        """Test getting complete TikTok metadata."""
        url = "https://www.tiktok.com/@user/video/123456789"
        metadata = self.handler.get_metadata(url)

        assert metadata["type"] == "video"
        assert metadata["video_id"] == "123456789"
        assert metadata["requires_auth"] is False

    def test_process_download(self):
        """Test TikTok download processing."""
        url = "https://www.tiktok.com/@user/video/123456789"
        options = {"test": "option"}

        result = self.handler.process_download(url, options)
        assert result is True

    def test_detect_tiktok_type_video(self):
        """Test TikTok type detection for video URLs."""
        url = "https://www.tiktok.com/@user/video/123456789"
        assert self.handler._detect_tiktok_type(url) == "video"

    def test_detect_tiktok_type_user_t(self):
        """Test TikTok type detection for /t/ URLs."""
        url = "https://www.tiktok.com/@user/t/123456789"
        assert self.handler._detect_tiktok_type(url) == "user"

    def test_detect_tiktok_type_user_link(self):
        """Test TikTok type detection for @tiktok.com URLs."""
        url = "https://username@tiktok.com"
        assert self.handler._detect_tiktok_type(url) == "user_link"

    def test_detect_tiktok_type_unknown(self):
        """Test TikTok type detection for unknown URL patterns."""
        url = "https://www.tiktok.com/unknown"
        assert self.handler._detect_tiktok_type(url) == "unknown"

    def test_extract_video_id_from_video_url(self):
        """Test extracting video ID from video URL."""
        url = "https://www.tiktok.com/@user/video/123456789"
        assert self.handler._extract_video_id(url) == "123456789"

    def test_extract_video_id_from_v_url(self):
        """Test extracting video ID from /v/ URL."""
        url = "https://www.tiktok.com/v/abc123-def456"
        assert self.handler._extract_video_id(url) == "abc123-def456"

    def test_extract_video_id_no_match(self):
        """Test extracting video ID from URL with no match."""
        url = "https://www.tiktok.com/@user"
        assert self.handler._extract_video_id(url) is None

    @patch("src.utils.type_helpers.get_root")
    @patch("src.utils.type_helpers.get_platform_callback")
    @patch("src.utils.type_helpers.schedule_on_main_thread")
    def test_get_ui_callback_success(self, mock_schedule, mock_get_callback, mock_get_root):
        """Test successful UI callback retrieval and execution."""
        mock_root = Mock()
        mock_get_root.return_value = mock_root

        mock_download_callback = Mock()
        mock_get_callback.return_value = mock_download_callback

        url = "https://www.tiktok.com/@user/video/123456789"
        ui_context = Mock()

        callback = self.handler.get_ui_callback()
        callback(url, ui_context)

        mock_get_root.assert_called_once_with(ui_context)
        mock_get_callback.assert_called_once_with(ui_context, "tiktok")
        mock_schedule.assert_called_once()

    @patch("src.utils.type_helpers.get_root")
    @patch("src.utils.type_helpers.get_platform_callback")
    def test_get_ui_callback_fallback_to_generic(self, mock_get_callback, mock_get_root):
        """Test UI callback falls back to generic when platform-specific not found."""
        mock_root = Mock()
        mock_get_root.return_value = mock_root

        # First call returns None (no tiktok callback), second returns generic callback
        mock_generic_callback = Mock()
        mock_get_callback.side_effect = [None, mock_generic_callback]

        url = "https://www.tiktok.com/@user/video/123456789"
        ui_context = Mock()

        callback = self.handler.get_ui_callback()
        callback(url, ui_context)

        # Should have called get_platform_callback twice - once for tiktok, once for generic
        assert mock_get_callback.call_count == 2

    @patch("src.utils.type_helpers.get_root")
    @patch("src.utils.type_helpers.get_platform_callback")
    def test_get_ui_callback_no_callback_found(self, mock_get_callback, mock_get_root):
        """Test UI callback when no callback found."""
        mock_root = Mock()
        mock_get_root.return_value = mock_root
        mock_get_callback.return_value = None

        url = "https://www.tiktok.com/@user/video/123456789"
        ui_context = Mock()

        callback = self.handler.get_ui_callback()
        callback(url, ui_context)

        # Should not raise exception, just log error
        assert mock_get_callback.call_count == 2  # tiktok + generic


class TestTikTokIntegration:
    """Integration tests for TikTok functionality."""

    def test_service_factory_tiktok_detection(self):
        """Test service factory detects TikTok URLs correctly."""
        from src.application.service_factory import ServiceFactory

        factory = ServiceFactory(cookie_manager=Mock())

        test_urls = [
            "https://www.tiktok.com/@user/video/123456789",
            "https://tiktok.com/@user/video/123456789",
            "https://vm.tiktok.com/XYZ123/",
        ]

        for url in test_urls:
            service_type = factory.detect_service_type(url)
            assert service_type == ServiceType.TIKTOK, f"Failed for URL: {url}"

    def test_tiktok_url_patterns_coverage(self):
        """Test TikTok URL patterns cover all common formats."""
        patterns = TikTokHandler.get_patterns()

        test_urls = [
            "https://www.tiktok.com/@user/video/123456789",
            "https://tiktok.com/@user/video/123456789",
            "https://vm.tiktok.com/XYZ123/",
            "https://tiktok.com/t/XYZ123",
        ]

        for url in test_urls:
            matched = any(re.search(pattern, url) for pattern in patterns)
            assert matched, f"No pattern matched URL: {url}"


if __name__ == "__main__":
    pytest.main([__file__])
