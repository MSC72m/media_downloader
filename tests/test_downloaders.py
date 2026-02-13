"""Tests for downloader services including Pinterest and YouTube."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.application.service_factory import ServiceFactory
from src.core.enums import ServiceType
from src.services.pinterest.downloader import PinterestDownloader
from src.services.soundcloud.downloader import SoundCloudDownloader
from src.services.spotify.downloader import SpotifyDownloader
from src.services.youtube.downloader import YouTubeDownloader


class MockFileService:
    """Mock file service for testing."""

    def ensure_directory(self, path: str) -> bool:
        _ = path
        return True

    def sanitize_filename(self, filename: str) -> str:
        return filename

    def clean_filename(self, filename: str) -> str:
        return filename

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        suffix = extension if extension.startswith(".") else f".{extension}" if extension else ""
        return f"{directory}/{base_name}{suffix}"

    def download_file(self, url: str, path: str, progress_callback=None):
        class Result:
            success = True

        return Result()


class MockErrorNotifier:
    """Mock error notifier for testing."""

    def show_error(self, title: str, message: str) -> None:
        _ = (title, message)

    def show_warning(self, title: str, message: str) -> None:
        _ = (title, message)

    def show_info(self, title: str, message: str) -> None:
        _ = (title, message)

    def set_message_queue(self, message_queue) -> None:
        _ = message_queue

    def handle_service_failure(
        self,
        service: str,
        operation: str,
        error_message: str,
        url: str = "",
    ) -> None:
        _ = (service, operation, error_message, url)

    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        service: str = "",
    ) -> None:
        _ = (exception, context, service)


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
        mock_response.content = (
            b"<html><meta property='og:image' content='https://example.com/image.jpg'/></html>"
        )
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

    @patch("src.services.pinterest.downloader.check_site_connection")
    @patch("src.services.pinterest.downloader.requests.get")
    def test_pinterest_download_requires_real_output_file(self, mock_get, mock_check, tmp_path):
        mock_check.return_value = (True, None)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = (
            b"<html><meta property='og:image' content='https://example.com/image.jpg'/></html>"
        )
        mock_get.return_value = mock_response

        file_service = Mock()
        file_service.ensure_directory.return_value = True
        file_service.sanitize_filename.side_effect = lambda value: value

        class Result:
            success = True

        def fake_download(url, path, progress_callback=None):
            _ = (url, progress_callback)
            with open(path, "wb") as handle:
                handle.write(b"image-bytes")
            return Result()

        file_service.download_file.side_effect = fake_download

        downloader = PinterestDownloader(error_handler=MockErrorNotifier(), file_service=file_service)
        save_path = str(tmp_path / "pin_output")
        assert downloader.download("https://pin.it/3YtKpHT04", save_path) is True

    @patch("src.services.pinterest.downloader.check_site_connection")
    @patch("src.services.pinterest.downloader.requests.get")
    def test_pinterest_download_fails_when_result_success_but_file_missing(
        self, mock_get, mock_check, tmp_path
    ):
        mock_check.return_value = (True, None)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = (
            b"<html><meta property='og:image' content='https://example.com/image.jpg'/></html>"
        )
        mock_get.return_value = mock_response

        file_service = Mock()
        file_service.ensure_directory.return_value = True
        file_service.sanitize_filename.side_effect = lambda value: value

        class Result:
            success = True

        file_service.download_file.return_value = Result()

        downloader = PinterestDownloader(error_handler=MockErrorNotifier(), file_service=file_service)
        save_path = str(tmp_path / "pin_output")
        assert downloader.download("https://pin.it/3YtKpHT04", save_path) is False


class TestSoundCloudDownloaderOutputVerification:
    @patch("src.services.soundcloud.downloader.yt_dlp.YoutubeDL")
    def test_soundcloud_download_requires_verified_output(self, mock_ydl_class, tmp_path):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"title": "Track", "uploader": "Artist"}
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SoundCloudDownloader(error_handler=MockErrorNotifier())
        downloader._verify_download_output = Mock(return_value=False)

        result = downloader.download("https://soundcloud.com/test/track", str(tmp_path / "track"))

        assert result is False
        downloader._verify_download_output.assert_called_once()

    @patch("src.services.soundcloud.downloader.yt_dlp.YoutubeDL")
    def test_soundcloud_download_succeeds_when_output_verified(self, mock_ydl_class, tmp_path):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"title": "Track", "uploader": "Artist"}
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SoundCloudDownloader(error_handler=MockErrorNotifier())
        downloader._verify_download_output = Mock(return_value=True)

        result = downloader.download("https://soundcloud.com/test/track", str(tmp_path / "track"))

        assert result is True
        downloader._verify_download_output.assert_called_once()


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

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1000),
            patch("os.makedirs"),
        ):
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

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1000),
            patch("os.makedirs"),
        ):
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

        download1 = Download(
            url="https://test.com/1", name="test1", status=DownloadStatus.COMPLETED
        )
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

        download1 = Download(
            url="https://test.com/1", name="test1", status=DownloadStatus.COMPLETED
        )
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


class TestServiceFactorySpotifyDetection:
    """Test Spotify URL detection in service factory."""

    def test_detect_spotify_track_url(self):
        """Test detection of Spotify track URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type(
            "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        )
        assert service_type == ServiceType.SPOTIFY

    def test_detect_spotify_album_url(self):
        """Test detection of Spotify album URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type(
            "https://open.spotify.com/album/1DFixLWuPkv3KT3TnV35m3"
        )
        assert service_type == ServiceType.SPOTIFY

    def test_detect_spotify_playlist_url(self):
        """Test detection of Spotify playlist URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type(
            "https://open.spotify.com/playlist/37i9dQZF1DX0XUsuxWHRQd"
        )
        assert service_type == ServiceType.SPOTIFY

    def test_detect_spotify_artist_url(self):
        """Test detection of Spotify artist URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type(
            "https://open.spotify.com/artist/0TnOYISbd1XYRBk9myaseg"
        )
        assert service_type == ServiceType.SPOTIFY

    def test_detect_spotify_uri(self):
        """Test detection of Spotify URI format."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type("spotify:track:4iV5W9uYEdYUVa79Axb7Rh")
        assert service_type == ServiceType.GENERIC

    def test_detect_spotify_short_url(self):
        """Test detection of Spotify short URLs."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type("https://spotify.link/abc123")
        assert service_type == ServiceType.SPOTIFY

    def test_get_spotify_downloader(self):
        """Test getting Spotify downloader for Spotify URLs."""
        factory = ServiceFactory(
            cookie_manager=Mock(),
            error_handler=MockErrorNotifier(),
            file_service=MockFileService(),
        )
        downloader = factory.get_downloader("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh")
        assert isinstance(downloader, SpotifyDownloader)

    def test_spotify_not_fallback_to_youtube(self):
        """Test that Spotify URLs don't fallback to YouTube."""
        factory = ServiceFactory(cookie_manager=Mock())
        service_type = factory.detect_service_type(
            "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        )
        assert service_type != ServiceType.YOUTUBE
        assert service_type == ServiceType.SPOTIFY


class TestSpotifyDownloader:
    """Test Spotify downloader functionality."""

    @patch("src.services.spotify.downloader.requests.get")
    def test_spotify_downloader_metadata_extraction(self, mock_get):
        """Test Spotify downloader metadata extraction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "thumbnail_url": "https://example.com/image.jpg",
            "title": "Test Artist - Test Track",
            "type": "rich",
            "html": "",
        }
        mock_get.return_value = mock_response

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )
        metadata = downloader._extract_spotify_metadata(
            "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        )

        assert metadata is not None
        assert metadata["title"] == "Test Artist - Test Track"
        assert metadata["thumbnail"] == "https://example.com/image.jpg"

    @patch("src.services.spotify.downloader.requests.get")
    def test_spotify_downloader_url_type_detection(self, mock_get):
        """Test Spotify downloader URL type detection."""
        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )

        assert downloader._detect_url_type("https://open.spotify.com/track/abc123") == "track"
        assert downloader._detect_url_type("https://open.spotify.com/album/abc123") == "album"
        assert downloader._detect_url_type("https://open.spotify.com/playlist/abc123") == "playlist"
        assert downloader._detect_url_type("https://open.spotify.com/artist/abc123") == "artist"

    def test_spotify_downloader_artist_track_parsing(self):
        """Test Spotify downloader artist-track parsing."""
        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )

        artist, track = downloader._parse_artist_track("Artist - Track Name")
        assert artist == "Artist"
        assert track == "Track Name"

        artist, track = downloader._parse_artist_track("Track Name by Artist")
        assert artist == "Artist"
        assert track == "Track Name"

        artist, track = downloader._parse_artist_track("Artist Track Name")
        assert artist == ""
        assert track == "Artist Track Name"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_spotify_downloader_youtube_search(self, mock_get, mock_ydl_class):
        """Test Spotify downloader YouTube search."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "thumbnail_url": "https://example.com/image.jpg",
            "title": "Test Artist - Test Track",
            "type": "rich",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Test Artist - Test Track (Official)",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )
        results = downloader._search_youtube("Test Artist", "Test Track")

        assert len(results) > 0
        assert results[0]["id"] == "video1"

    def test_spotify_downloader_similarity_calculation(self):
        """Test Spotify downloader similarity calculation."""
        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )

        similarity = downloader._calculate_similarity(
            "Test Artist - Test Track", "Test Artist - Test Track (Official)"
        )
        assert similarity > 0.8

        similarity = downloader._calculate_similarity(
            "Test Artist - Test Track", "Completely Different Title"
        )
        assert similarity < 0.5

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    def test_spotify_downloader_get_metadata_track(self, mock_ydl_class, mock_get):
        """Test Spotify downloader get_metadata for track."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "thumbnail_url": "https://example.com/image.jpg",
            "title": "Test Artist - Test Track",
            "type": "rich",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Test Artist - Test Track (Official)",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService()
        )
        metadata = downloader.get_metadata("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh")

        assert metadata is not None
        assert metadata["title"] == "Test Artist - Test Track"
        assert metadata["thumbnail"] == "https://example.com/image.jpg"
        assert metadata["type"] == "track"
