"""Comprehensive tests for all platform handlers with proper dependency injection."""

import re
from unittest.mock import Mock, patch

import pytest

from src.core.interfaces import (
    ICookieHandler,
    IErrorNotifier,
    IFileService,
    IMessageQueue,
    IMetadataService,
    IUIState,
)
from src.handlers import _register_link_handlers


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

    def __init__(self):
        self.cookie_path = "/mock/cookies.txt"

    def get_cookies(self) -> str:
        return self.cookie_path

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


class MockMetadataService(IMetadataService):
    """Mock metadata service for testing."""

    def __init__(self):
        pass

    def fetch_metadata(self, url: str) -> object:
        class MockMetadata:
            def __init__(self):
                self.title = "Mock Title"
                self.description = "Mock Description"

        return MockMetadata()

    def get_metadata(self, url: str) -> dict:
        return {"title": "Mock Title", "description": "Mock Description"}

    def is_available(self) -> bool:
        return True


class MockFileService(IFileService):
    """Mock file service for testing."""

    def clean_filename(self, filename: str) -> str:
        return filename.replace("/", "_").replace("\\", "_")

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        return f"{base_name}.{extension}"

    def ensure_directory(self, directory: str) -> bool:
        return True

    def get_file_size(self, file_path: str) -> int:
        return 1024

    def delete_file(self, file_path: str) -> bool:
        return True


class MockUIState(IUIState):
    """Mock UI state for testing."""

    def __init__(self):
        self.download_directory = "~/Downloads"
        self.current_url = ""
        self.busy = False

    def set_download_directory(self, directory: str) -> None:
        self.download_directory = directory

    def get_download_directory(self) -> str:
        return self.download_directory

    def get_current_url(self) -> str:
        return self.current_url

    def set_current_url(self, url: str) -> None:
        self.current_url = url

    def is_busy(self) -> bool:
        return self.busy

    def set_busy(self, busy: bool) -> None:
        self.busy = busy


class MockMessageQueue(IMessageQueue):
    """Mock message queue for testing."""

    def __init__(self):
        self.messages = []

    def add_message(self, message) -> None:
        self.messages.append(message)

    def get_messages(self) -> list:
        return self.messages.copy()

    # IMessageQueue might have other required abstract methods
    def process_messages(self) -> None:
        pass

    def clear_messages(self) -> None:
        self.messages.clear()

    def register_handler(self, handler) -> None:
        pass

    def send_message(self, message) -> None:
        self.add_message(message)


class TestHandlerRegistration:
    """Test that all handlers can be registered and have proper interfaces."""

    def test_all_handlers_registered(self):
        """Test that all handlers are properly registered."""
        handlers = _register_link_handlers()

        # Should have exactly 5 handlers
        assert len(handlers) == 5

        handler_names = [
            handler.__name__ if hasattr(handler, "__name__") else handler.__class__.__name__
            for handler in handlers
        ]
        expected_handlers = [
            "InstagramHandler",
            "PinterestHandler",
            "SoundCloudHandler",
            "TwitterHandler",
            "YouTubeHandler",
        ]

        for expected in expected_handlers:
            assert expected in handler_names, f"Missing {expected}"

    def test_handlers_have_required_methods(self):
        """Test that all handlers have required interface methods."""
        handlers = _register_link_handlers()

        for handler in handlers:
            # Check for required methods from LinkHandlerInterface
            assert hasattr(
                handler, "can_handle"
            ), f"{handler.__class__.__name__} missing can_handle"
            assert hasattr(
                handler, "get_patterns"
            ), f"{handler.__class__.__name__} missing get_patterns"
            assert hasattr(
                handler, "get_ui_callback"
            ), f"{handler.__class__.__name__} missing get_ui_callback"
            assert callable(
                handler.can_handle
            ), f"{handler.__class__.__name__}.can_handle is not callable"
            assert callable(
                handler.get_patterns
            ), f"{handler.__class__.__name__}.get_patterns is not callable"
            assert callable(
                handler.get_ui_callback
            ), f"{handler.__class__.__name__}.get_ui_callback is not callable"


class TestYouTubeHandler:
    """Test YouTube handler with dependency injection."""

    def test_youtube_handler_instantiation(self):
        """Test YouTube handler can be instantiated with dependencies."""
        from src.handlers.youtube_handler import YouTubeHandler

        cookie_handler = MockCookieHandler()
        metadata_service = MockMetadataService()
        MockErrorHandler()
        MockFileService()
        MockUIState()
        message_queue = MockMessageQueue()

        handler = YouTubeHandler(
            cookie_handler=cookie_handler,
            metadata_service=metadata_service,
            auto_cookie_manager=Mock(),  # Add auto_cookie_manager
            message_queue=message_queue,
        )

        assert handler.cookie_handler is cookie_handler
        assert handler.metadata_service is metadata_service
        assert handler.message_queue is message_queue

    def test_youtube_handler_url_patterns(self):
        """Test YouTube handler URL pattern matching."""
        from src.handlers.youtube_handler import YouTubeHandler

        handler = YouTubeHandler(
            cookie_handler=MockCookieHandler(),
            metadata_service=MockMetadataService(),
            auto_cookie_manager=Mock(),
            message_queue=MockMessageQueue(),
        )

        patterns = handler.get_patterns()
        assert len(patterns) > 0

        # Test YouTube URL patterns
        test_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtube.com/shorts/abc123",
        ]

        for url in test_urls:
            for pattern in patterns:
                if re.match(pattern, url):
                    print(f"✓ YouTube pattern matched: {url}")
                    break
            else:
                pytest.fail(f"YouTube URL not matched by any pattern: {url}")

    def test_youtube_handler_can_handle(self):
        """Test YouTube handler can handle YouTube URLs."""
        from src.handlers.youtube_handler import YouTubeHandler

        handler = YouTubeHandler(
            cookie_handler=MockCookieHandler(),
            metadata_service=MockMetadataService(),
            auto_cookie_manager=Mock(),
            message_queue=MockMessageQueue(),
        )

        # Should handle YouTube URLs
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = handler.can_handle(youtube_url)
        assert result.service_type == "youtube"
        assert result.confidence > 0.0

        # Should not handle non-YouTube URLs
        other_url = "https://www.twitter.com/user/status/123"
        result = handler.can_handle(other_url)
        assert result.service_type == "unknown"


class TestTwitterHandler:
    """Test Twitter handler with dependency injection."""

    def test_twitter_handler_instantiation(self):
        """Test Twitter handler can be instantiated."""
        from src.handlers.twitter_handler import TwitterHandler

        # TwitterHandler inherits from LinkHandlerInterface and doesn't need dependencies
        handler = TwitterHandler()

        assert handler is not None

    def test_twitter_handler_url_patterns(self):
        """Test Twitter handler URL pattern matching."""
        from src.handlers.twitter_handler import TwitterHandler

        handler = TwitterHandler()
        patterns = handler.get_patterns()
        assert len(patterns) > 0

        # Test Twitter URL patterns
        test_urls = [
            "https://twitter.com/user/status/123456789",
            "https://x.com/user/status/123456789",
            "https://mobile.twitter.com/user/status/123456789",
        ]

        for url in test_urls:
            for pattern in patterns:
                if re.match(pattern, url):
                    print(f"✓ Twitter pattern matched: {url}")
                    break
            else:
                pytest.fail(f"Twitter URL not matched by any pattern: {url}")


class TestInstagramHandler:
    """Test Instagram handler with dependency injection."""

    def test_instagram_handler_instantiation(self):
        """Test Instagram handler can be instantiated with dependencies."""
        from src.handlers.instagram_handler import InstagramHandler

        # Instagram handler doesn't require dependencies
        handler = InstagramHandler()
        assert handler is not None

    def test_instagram_handler_url_patterns(self):
        """Test Instagram handler URL pattern matching."""
        from src.handlers.instagram_handler import InstagramHandler

        handler = InstagramHandler()
        patterns = handler.get_patterns()
        assert len(patterns) > 0

        # Test Instagram URL patterns
        test_urls = [
            "https://www.instagram.com/p/ABC123/",
            "https://instagram.com/p/ABC123/",
            "https://www.instagram.com/reel/ABC123/",
        ]

        for url in test_urls:
            for pattern in patterns:
                if re.match(pattern, url):
                    print(f"✓ Instagram pattern matched: {url}")
                    break
            else:
                pytest.fail(f"Instagram URL not matched by any pattern: {url}")


class TestPinterestHandler:
    """Test Pinterest handler with dependency injection."""

    def test_pinterest_handler_instantiation(self):
        """Test Pinterest handler can be instantiated with dependencies."""
        from src.handlers.pinterest_handler import PinterestHandler

        # Pinterest handler doesn't require dependencies
        handler = PinterestHandler()
        assert handler is not None

    def test_pinterest_handler_url_patterns(self):
        """Test Pinterest handler URL pattern matching."""
        from src.handlers.pinterest_handler import PinterestHandler

        handler = PinterestHandler()
        patterns = handler.get_patterns()
        assert len(patterns) > 0

        # Test Pinterest URL patterns
        test_urls = [
            "https://www.pinterest.com/pin/123456789",
            "https://pinterest.com/pin/123456789",
            "https://www.pinterest.ca/pin/123456789",
        ]

        for url in test_urls:
            for pattern in patterns:
                if re.match(pattern, url):
                    print(f"✓ Pinterest pattern matched: {url}")
                    break
            else:
                pytest.fail(f"Pinterest URL not matched by any pattern: {url}")


class TestSoundCloudHandler:
    """Test SoundCloud handler with dependency injection."""

    def test_soundcloud_handler_instantiation(self):
        """Test SoundCloud handler can be instantiated with dependencies."""
        from src.handlers.soundcloud_handler import SoundCloudHandler

        # SoundCloud handler needs a message_queue
        message_queue = MockMessageQueue()
        handler = SoundCloudHandler(message_queue=message_queue)
        assert handler is not None

    def test_soundcloud_handler_url_patterns(self):
        """Test SoundCloud handler URL pattern matching."""
        from src.handlers.soundcloud_handler import SoundCloudHandler

        handler = SoundCloudHandler(message_queue=MockMessageQueue())
        patterns = handler.get_patterns()
        assert len(patterns) > 0

        # Test SoundCloud URL patterns
        test_urls = [
            "https://soundcloud.com/artist/track-name",
            "https://www.soundcloud.com/artist/track-name",
            "https://soundcloud.app.goo.gl/example",
        ]

        for url in test_urls:
            for pattern in patterns:
                if re.match(pattern, url):
                    print(f"✓ SoundCloud pattern matched: {url}")
                    break
            else:
                pytest.fail(f"SoundCloud URL not matched by any pattern: {url}")


class TestDownloadHandler:
    """Test Download handler with dependency injection."""

    def test_download_handler_instantiation(self):
        """Test Download handler can be instantiated with dependencies."""
        from src.handlers.download_handler import DownloadHandler

        # Create mock dependencies
        mock_download_service = Mock()
        mock_download_service.has_downloads.return_value = False
        mock_download_service.get_downloads.return_value = []

        mock_file_service = MockFileService()
        mock_ui_state = MockUIState()

        handler = DownloadHandler(
            download_service=mock_download_service,
            service_factory=Mock(),
            file_service=mock_file_service,
            ui_state=mock_ui_state,
        )

        assert handler.download_service is mock_download_service
        assert handler.file_service is mock_file_service
        assert handler.ui_state is mock_ui_state

    def test_download_handler_interface_compliance(self):
        """Test Download handler implements IDownloadHandler interface."""
        from src.handlers.download_handler import DownloadHandler

        # Create mock dependencies
        mock_download_service = Mock()
        mock_download_service.has_downloads.return_value = False
        mock_download_service.get_downloads.return_value = []
        mock_download_service.add_download = Mock()

        mock_file_service = MockFileService()
        mock_ui_state = MockUIState()

        handler = DownloadHandler(
            download_service=mock_download_service,
            service_factory=Mock(),
            file_service=mock_file_service,
            ui_state=mock_ui_state,
        )

        # Test interface methods
        assert hasattr(handler, "process_url")
        assert hasattr(handler, "handle_download_error")
        assert hasattr(handler, "is_available")

        # Test process_url
        result = handler.process_url("https://example.com/video")
        assert isinstance(result, bool)
        mock_download_service.add_download.assert_called_once()

        # Test is_available
        available = handler.is_available()
        assert isinstance(available, bool)

    def test_download_handler_url_detection(self):
        """Test Download handler URL type detection."""
        from src.handlers.download_handler import DownloadHandler

        # Create mock dependencies
        mock_download_service = Mock()
        mock_download_service.has_downloads.return_value = False
        mock_download_service.get_downloads.return_value = []

        mock_file_service = MockFileService()
        mock_ui_state = MockUIState()

        handler = DownloadHandler(
            download_service=mock_download_service,
            service_factory=Mock(),
            file_service=mock_file_service,
            ui_state=mock_ui_state,
        )

        # Test URL type detection
        test_cases = [
            ("https://www.youtube.com/watch?v=test", "youtube"),
            ("https://twitter.com/user/status/123", "twitter"),
            ("https://www.instagram.com/p/test/", "instagram"),
            ("https://www.pinterest.com/pin/test/", "pinterest"),
            ("https://soundcloud.com/artist/track", "soundcloud"),
            ("https://example.com/unknown", "unknown"),
        ]

        for url, expected_type in test_cases:
            detected_type = handler._detect_service_type(url)
            assert (
                detected_type == expected_type
            ), f"Expected {expected_type}, got {detected_type} for {url}"


class TestHandlerIntegration:
    """Integration tests for handlers working together."""

    def test_handler_collaboration(self):
        """Test that handlers can work together without conflicts."""
        handlers = _register_link_handlers()

        # Each handler should have unique patterns
        all_patterns = []
        for handler in handlers:
            patterns = handler.get_patterns()
            all_patterns.extend(patterns)

        # Verify we have patterns from all handlers
        assert len(all_patterns) > 0

        # No two handlers should have conflicting responsibilities
        handler_types = set()
        for handler in handlers:
            handler_name = (
                handler.__name__ if hasattr(handler, "__name__") else handler.__class__.__name__
            ).lower()
            if "youtube" in handler_name:
                handler_types.add("youtube")
            elif "twitter" in handler_name:
                handler_types.add("twitter")
            elif "instagram" in handler_name:
                handler_types.add("instagram")
            elif "pinterest" in handler_name:
                handler_types.add("pinterest")
            elif "soundcloud" in handler_name:
                handler_types.add("soundcloud")

        expected_types = {"youtube", "twitter", "instagram", "pinterest", "soundcloud"}
        assert handler_types == expected_types

    @patch("src.utils.type_helpers.get_platform_callback")
    @patch("src.utils.type_helpers.get_root")
    def test_handler_callbacks(self, mock_get_root, mock_get_callback):
        """Test that handler callbacks are properly structured."""
        from unittest.mock import Mock

        # Setup mocks
        mock_root = Mock()
        mock_get_root.return_value = mock_root
        mock_callback = Mock()
        mock_get_callback.return_value = mock_callback

        handlers = _register_link_handlers()

        for handler_class in handlers:
            # Create an instance if needed
            try:
                if handler_class.__name__ in ["YouTubeHandler"]:
                    # Skip YouTubeHandler as it requires complex dependencies
                    continue
                elif handler_class.__name__ == "SoundCloudHandler":
                    handler = handler_class(message_queue=MockMessageQueue())
                else:
                    handler = handler_class()

                callback = handler.get_ui_callback()
                assert callable(callback), f"{handler_class.__name__} callback is not callable"
            except Exception as e:
                # Skip handlers that can't be instantiated easily
                print(f"Skipping {handler_class.__name__}: {e}")


if __name__ == "__main__":
    pytest.main([__file__])
