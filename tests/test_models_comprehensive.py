"""Comprehensive tests for core models to achieve 100% coverage."""

from datetime import datetime

from src.core.enums.download_status import DownloadStatus
from src.core.enums.service_type import ServiceType
from src.core.models import AuthState, ButtonState, Download, DownloadOptions, UIState


class TestDownloadComprehensive:
    """Comprehensive tests for Download model."""

    def test_download_creation_with_all_fields(self):
        """Test Download creation with all possible fields."""
        created_at = datetime.now()
        completed_at = datetime.now()

        download = Download(
            name="Comprehensive Test Video",
            url="https://example.com/comprehensive",
            status=DownloadStatus.DOWNLOADING,
            progress=50.5,
            speed=1024.0,
            created_at=created_at,
            completed_at=completed_at,
            error_message="Test error",
            service_type=ServiceType.YOUTUBE,
            quality="1080p",
            format="video",
            audio_only=False,
            video_only=False,
            download_playlist=True,
            download_subtitles=True,
            selected_subtitles=[
                {"language_code": "en", "language_name": "English"},
                {"language_code": "es", "language_name": "Spanish"},
            ],
            download_thumbnail=True,
            embed_metadata=True,
            cookie_path="/path/to/cookies",
            speed_limit=1000000,
            retries=5,
            concurrent_downloads=2,
        )

        # Test all attributes
        assert download.name == "Comprehensive Test Video"
        assert download.url == "https://example.com/comprehensive"
        assert download.status == DownloadStatus.DOWNLOADING
        assert download.progress == 50.5
        assert download.speed == 1024.0
        assert download.created_at == created_at
        assert download.completed_at == completed_at
        assert download.error_message == "Test error"
        assert download.service_type == ServiceType.YOUTUBE
        assert download.quality == "1080p"
        assert download.format == "video"
        assert download.audio_only is False
        assert download.video_only is False
        assert download.download_playlist is True
        assert download.download_subtitles is True
        assert len(download.selected_subtitles) == 2
        assert download.download_thumbnail is True
        assert download.embed_metadata is True
        assert download.cookie_path == "/path/to/cookies"
        assert download.speed_limit == 1000000
        assert download.retries == 5
        assert download.concurrent_downloads == 2

    def test_download_creation_with_minimal_fields(self):
        """Test Download creation with minimal required fields."""
        download = Download(name="Minimal Video", url="https://example.com/minimal")

        # Test defaults
        assert download.name == "Minimal Video"
        assert download.url == "https://example.com/minimal"
        assert download.status == DownloadStatus.PENDING
        assert download.progress == 0.0
        assert download.speed == 0.0
        assert download.quality == "720p"
        assert download.format == "video"
        assert download.audio_only is False
        assert download.video_only is False
        assert download.download_playlist is False
        assert download.download_subtitles is False
        assert download.download_thumbnail is True
        assert download.embed_metadata is True
        assert download.retries == 3
        assert download.concurrent_downloads == 1

    def test_download_with_different_service_types(self):
        """Test Download with different service types."""
        services = [
            ServiceType.YOUTUBE,
            ServiceType.TWITTER,
            ServiceType.INSTAGRAM,
            ServiceType.PINTEREST,
        ]

        for service in services:
            download = Download(
                name=f"Video from {service}",
                url=f"https://{service}.com/video",
                service_type=service,
            )
            assert download.service_type == service

    def test_download_with_different_statuses(self):
        """Test Download with different statuses."""
        statuses = [
            DownloadStatus.PENDING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.PAUSED,
            DownloadStatus.CANCELLED,
        ]

        for status in statuses:
            download = Download(
                name=f"Video with {status} status",
                url="https://example.com/video",
                status=status,
            )
            assert download.status == status

    def test_download_with_edge_case_values(self):
        """Test Download with edge case values."""
        download = Download(
            name="",  # Empty name
            url="",  # Empty URL
            progress=-1.0,  # Negative progress
            speed=0.0,  # Zero speed
            quality="",  # Empty quality
            format="",  # Empty format
            retries=0,  # Zero retries
            concurrent_downloads=0,  # Zero concurrent downloads
        )

        assert download.name == ""
        assert download.url == ""
        assert download.progress == -1.0
        assert download.speed == 0.0
        assert download.quality == ""
        assert download.format == ""
        assert download.retries == 0
        assert download.concurrent_downloads == 0


class TestDownloadOptionsComprehensive:
    """Comprehensive tests for DownloadOptions model."""

    def test_download_options_with_all_fields(self):
        """Test DownloadOptions with all possible fields."""
        options = DownloadOptions(save_directory="/custom/download/path")

        assert options.save_directory == "/custom/download/path"

    def test_download_options_with_defaults(self):
        """Test DownloadOptions with default values."""
        options = DownloadOptions()

        # The default expands ~/Downloads to the actual path
        assert options.save_directory is not None
        assert len(options.save_directory) > 0


class TestUIStateComprehensive:
    """Comprehensive tests for UIState model."""

    def test_ui_state_creation(self):
        """Test UIState creation."""
        ui_state = UIState()
        assert ui_state is not None

    def test_ui_state_with_fields(self):
        """Test UIState with various fields."""
        ui_state = UIState(
            download_directory="/custom/downloads",
            show_options_panel=True,
            selected_indices=[0, 1, 2],
        )

        assert ui_state.download_directory == "/custom/downloads"
        assert ui_state.show_options_panel is True
        assert ui_state.selected_indices == [0, 1, 2]


class TestAuthStateComprehensive:
    """Comprehensive tests for AuthState model."""

    def test_auth_state_creation(self):
        """Test AuthState creation."""
        auth_state = AuthState()
        assert auth_state is not None

    def test_auth_state_with_fields(self):
        """Test AuthState with various fields."""
        auth_state = AuthState(is_authenticated=True, service="youtube", username="testuser")

        assert auth_state.is_authenticated is True
        assert auth_state.service == "youtube"
        assert auth_state.username == "testuser"


class TestButtonStateComprehensive:
    """Comprehensive tests for ButtonState model."""

    def test_button_state_enum_values(self):
        """Test ButtonState enum values."""
        assert ButtonState.REMOVE == "remove"
        assert ButtonState.CLEAR == "clear"
        assert ButtonState.DOWNLOAD == "download"
        assert ButtonState.SETTINGS == "settings"
        assert ButtonState.CANCEL == "cancel"

    def test_button_state_enum_usage(self):
        """Test ButtonState enum usage."""
        # Test that we can use the enum values
        remove_state = ButtonState.REMOVE
        download_state = ButtonState.DOWNLOAD

        assert remove_state == "remove"
        assert download_state == "download"
