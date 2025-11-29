"""Tests for core models."""

from src.core.enums.download_status import DownloadStatus
from src.core.enums.service_type import ServiceType
from src.core.models import AuthState, ButtonState, Download, DownloadOptions, UIState


class TestDownload:
    """Test Download model."""

    def test_download_creation_with_defaults(self):
        """Test Download creation with default values."""
        download = Download(
            name="Test Video",
            url="https://example.com/video",
            service_type=ServiceType.YOUTUBE,
        )

        assert download.name == "Test Video"
        assert download.url == "https://example.com/video"
        assert download.service_type == ServiceType.YOUTUBE
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

    def test_download_creation_with_custom_values(self):
        """Test Download creation with custom values."""
        download = Download(
            name="Custom Video",
            url="https://example.com/custom",
            service_type=ServiceType.INSTAGRAM,
            quality="1080p",
            audio_only=True,
            download_subtitles=True,
            retries=5,
        )

        assert download.name == "Custom Video"
        assert download.url == "https://example.com/custom"
        assert download.service_type == ServiceType.INSTAGRAM
        assert download.quality == "1080p"
        assert download.audio_only is True
        assert download.download_subtitles is True
        assert download.retries == 5

    def test_download_with_subtitles(self):
        """Test Download with subtitle selection."""
        subtitles = [
            {"language_code": "en", "language_name": "English"},
            {"language_code": "es", "language_name": "Spanish"},
        ]

        download = Download(
            name="Video with Subtitles",
            url="https://example.com/subtitles",
            service_type=ServiceType.YOUTUBE,
            download_subtitles=True,
            selected_subtitles=subtitles,
        )

        assert download.download_subtitles is True
        assert len(download.selected_subtitles) == 2
        assert download.selected_subtitles[0]["language_code"] == "en"
        assert download.selected_subtitles[1]["language_code"] == "es"


class TestDownloadOptions:
    """Test DownloadOptions model."""

    def test_download_options_default(self):
        """Test DownloadOptions with default values."""
        options = DownloadOptions()

        # The default expands ~/Downloads to the actual path
        assert options.save_directory is not None
        assert len(options.save_directory) > 0

    def test_download_options_custom(self):
        """Test DownloadOptions with custom values."""
        options = DownloadOptions(save_directory="/custom/path")

        assert options.save_directory == "/custom/path"


class TestUIState:
    """Test UIState model."""

    def test_ui_state_creation(self):
        """Test UIState creation."""
        ui_state = UIState()

        # UIState should be creatable
        assert ui_state is not None


class TestAuthState:
    """Test AuthState model."""

    def test_auth_state_creation(self):
        """Test AuthState creation."""
        auth_state = AuthState()

        # AuthState should be creatable
        assert auth_state is not None


class TestButtonState:
    """Test ButtonState model."""

    def test_button_state_creation(self):
        """Test ButtonState enum values."""
        # ButtonState is a StrEnum, test its values
        assert ButtonState.REMOVE == "remove"
        assert ButtonState.CLEAR == "clear"
        assert ButtonState.DOWNLOAD == "download"
        assert ButtonState.SETTINGS == "settings"
        assert ButtonState.CANCEL == "cancel"
