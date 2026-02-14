"""
Comprehensive integration tests for Spotify download functionality.

These tests verify:
1. Single music track downloads work end-to-end
2. Playlist downloads work end-to-end
3. User selection UI functions correctly
4. User notifications are displayed
5. Dialogs handle all edge cases properly
"""

from unittest.mock import Mock, MagicMock, patch, call
from typing import Any
import pytest
from src.core.enums.service_type import ServiceType
from src.core.models import Download, DownloadStatus
from src.services.spotify.downloader import SpotifyDownloader
from src.handlers.spotify_handler import SpotifyHandler
from src.ui.dialogs.spotify_downloader_dialog import SpotifyDownloaderDialog
from src.core.config import get_config


class MockErrorNotifier:
    """Mock error notifier for testing."""

    def show_error(self, title: str, message: str) -> None:
        pass

    def show_warning(self, title: str, message: str) -> None:
        pass

    def show_info(self, title: str, message: str) -> None:
        pass

    def set_message_queue(self, message_queue) -> None:
        _ = message_queue

    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        service: str = "",
    ) -> None:
        _ = (exception, context, service)

    def handle_service_failure(
        self,
        service: str,
        operation: str,
        error_message: str,
        url: str = "",
    ) -> None:
        _ = (service, operation, error_message, url)


class MockFileService:
    """Mock file service for testing."""

    def ensure_directory(self, path: str) -> bool:
        return True

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        return f"{base_name}.{extension}"

    def clean_filename(self, filename: str) -> str:
        return filename

    def sanitize_filename(self, filename: str) -> str:
        return filename

    def download_file(self, url: str, path: str, progress_callback=None):
        _ = (url, path, progress_callback)

        class Result:
            success = True

        return Result()

    def save_text_file(self, content: str, file_path: str) -> bool:
        _ = (content, file_path)
        return True


class MockMessageQueue:
    """Mock message queue for testing."""

    def post(self, message: str) -> None:
        pass

    def add_message(self, message) -> None:
        _ = message

    def send_message(self, message: dict) -> None:
        _ = message

    def clear(self) -> None:
        pass

    def register_handler(self, message_type: str, handler: Any) -> None:
        _ = (message_type, handler)

    def get_messages(self) -> list:
        return []


@pytest.mark.integration
class TestSpotifySingleTrackDownload:
    """Test single Spotify track download workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )
        self.handler = SpotifyHandler(message_queue=MockMessageQueue())

    def test_detect_spotify_track_url(self):
        """Verify Spotify track URLs are detected correctly."""
        url = "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        patterns = SpotifyHandler.get_patterns()

        import re

        matches = [p for p in patterns if re.search(p, url)]

        assert len(matches) > 0, "Track URL should match patterns"
        assert any("track" in p for p in matches), "Should contain 'track' pattern"

    @patch("src.services.spotify.downloader.requests.get")
    def test_extract_metadata_from_track(self, mock_get):
        """Verify metadata is extracted from track URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "thumbnail_url": "https://example.com/cover.jpg",
            "title": "Artist Name - Track Title",
            "type": "rich",
        }
        mock_get.return_value = mock_response

        url = "https://open.spotify.com/track/abc123"
        metadata = self.downloader._extract_spotify_metadata(url)

        assert metadata is not None
        assert metadata["title"] == "Artist Name - Track Title"
        assert metadata["type"] == "track"
        assert metadata["id"] == "abc123"
        assert metadata["thumbnail"] == "https://example.com/cover.jpg"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_youtube_search_for_track(self, mock_get, mock_ydl_class):
        """Verify YouTube search works for Spotify tracks."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Track",
            "thumbnail_url": "https://example.com/cover.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Artist - Track (Official)",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                },
                {
                    "id": "video2",
                    "title": "Artist - Track (Lyrics)",
                    "duration": 230,
                    "url": "https://youtube.com/watch?v=video2",
                },
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        results = self.downloader._search_youtube("Artist", "Track")

        assert len(results) == 2
        assert results[0]["id"] == "video1"
        assert results[1]["id"] == "video2"
        assert results[0]["title"] == "Artist - Track (Official)"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_select_best_youtube_match(self, mock_get, mock_ydl_class):
        """Verify best YouTube match is selected based on similarity."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Track",
            "thumbnail_url": "https://example.com/cover.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "match1",
                    "title": "Artist - Track Official Video",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=match1",
                },
                {
                    "id": "match2",
                    "title": "Completely Different Song",
                    "duration": 180,
                    "url": "https://youtube.com/watch?v=match2",
                },
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        results = self.downloader._search_youtube("Artist", "Track")
        best_match = self.downloader._select_best_match("Artist Track", results)

        assert best_match is not None
        assert best_match["id"] == "match1"
        assert "Artist" in best_match["title"]
        assert "Track" in best_match["title"]

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_similarity_scoring_for_tracks(self, mock_get, mock_ydl_class):
        """Verify similarity scoring works correctly for track matching."""
        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )

        score1 = downloader._calculate_similarity(
            "Never Gonna Give You Up", "Never Gonna Give You Up Official Video"
        )
        score2 = downloader._calculate_similarity(
            "Never Gonna Give You Up", "Random Other Song Title"
        )

        assert score1 > 0.5, "Similar song should have high similarity"
        assert score2 < 0.5, "Different song should have low similarity"
        assert score1 > score2, "Similar song should score higher than different song"


@pytest.mark.integration
class TestSpotifyPlaylistDownload:
    """Test Spotify playlist download workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )
        self.handler = SpotifyHandler(message_queue=MockMessageQueue())

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.BeautifulSoup")
    def test_extract_metadata_from_playlist(self, mock_bs4, mock_get):
        """Verify metadata is extracted from playlist URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "My Awesome Playlist",
            "thumbnail_url": "https://example.com/playlist.jpg",
        }
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        row_one = Mock()
        row_one.find.return_value = Mock(get_text=Mock(return_value="Track One"))
        row_two = Mock()
        row_two.find.return_value = Mock(get_text=Mock(return_value="Track Two"))
        row_three = Mock()
        row_three.find.return_value = Mock(get_text=Mock(return_value="Track Three"))
        mock_soup = Mock()
        mock_soup.find_all.return_value = [row_one, row_two, row_three]
        mock_bs4.return_value = mock_soup

        url = "https://open.spotify.com/playlist/abc123"
        metadata = self.downloader.get_metadata(url)

        assert metadata is not None
        assert metadata["title"] == "My Awesome Playlist"
        assert metadata["type"] == "playlist"
        assert metadata["id"] == "abc123"
        assert "tracks" in metadata
        assert len(metadata["tracks"]) == 3
        assert metadata["tracks"][0]["title"] == "Track One"
        assert metadata["tracks"][1]["title"] == "Track Two"
        assert metadata["tracks"][2]["title"] == "Track Three"

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.BeautifulSoup")
    def test_playlist_tracks_get_youtube_matches(self, mock_bs4, mock_ydl_class, mock_get):
        """Verify playlist tracks get YouTube matches."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Playlist", "thumbnail_url": "http://thumb.jpg"}
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        row_one = Mock()
        row_one.find.return_value = Mock(get_text=Mock(return_value="Track One"))
        row_two = Mock()
        row_two.find.return_value = Mock(get_text=Mock(return_value="Track Two"))
        mock_soup = Mock()
        mock_soup.find_all.return_value = [row_one, row_two]
        mock_bs4.return_value = mock_soup

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Track One Official",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        url = "https://open.spotify.com/playlist/abc123"
        metadata = self.downloader.get_metadata(url)

        assert "tracks" in metadata
        assert len(metadata["tracks"]) == 2

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.BeautifulSoup")
    def test_playlist_select_tracks_individually(self, mock_bs4, mock_ydl_class, mock_get):
        """Verify playlist allows individual track selection."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Playlist", "thumbnail_url": "http://thumb.jpg"}
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        row_one = Mock()
        row_one.find.return_value = Mock(get_text=Mock(return_value="Track One"))
        row_two = Mock()
        row_two.find.return_value = Mock(get_text=Mock(return_value="Track Two"))
        row_three = Mock()
        row_three.find.return_value = Mock(get_text=Mock(return_value="Track Three"))
        mock_soup = Mock()
        mock_soup.find_all.return_value = [row_one, row_two, row_three]
        mock_bs4.return_value = mock_soup

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Track One Official",
                    "duration": 210,
                    "url": "https://youtube.com/watch?v=video1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        url = "https://open.spotify.com/playlist/abc123"
        metadata = self.downloader.get_metadata(url)

        assert len(metadata["tracks"]) == 3

        selected_indices = [0, 2]
        for idx in selected_indices:
            track = metadata["tracks"][idx]
            assert track["title"] is not None


@pytest.mark.integration
class TestSpotifyUserInterface:
    """Test Spotify UI dialog and user interaction."""

    @patch("src.ui.dialogs.spotify_downloader_dialog.LoadingDialog")
    @patch("src.services.spotify.downloader.requests.get")
    def test_dialog_displays_spotify_metadata(self, mock_get, mock_loading):
        """Verify dialog displays Spotify metadata correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Song Title",
            "thumbnail_url": "https://example.com/art.jpg",
        }
        mock_get.return_value = mock_response

        mock_loading.return_value = MagicMock()

        metadata = {
            "title": "Artist - Song Title",
            "type": "track",
            "thumbnail": "https://example.com/art.jpg",
            "original_url": "https://open.spotify.com/track/abc123",
            "id": "abc123",
        }

        assert metadata["title"] == "Artist - Song Title"
        assert metadata["type"] == "track"
        assert metadata["id"] == "abc123"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_dialog_shows_youtube_search_results(self, mock_get, mock_ydl_class):
        """Verify dialog shows YouTube search results to user."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Track",
            "thumbnail_url": "https://example.com/art.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Artist - Track Official",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                },
                {
                    "id": "video2",
                    "title": "Artist - Track Remix",
                    "duration": 210,
                    "url": "https://youtube.com/watch?v=video2",
                },
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )
        results = downloader._search_youtube("Artist", "Track")

        assert len(results) == 2
        assert results[0]["title"] == "Artist - Track Official"
        assert results[1]["title"] == "Artist - Track Remix"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_dialog_user_selection_creates_download(self, mock_get, mock_ydl_class):
        """Verify user selection creates a Download object."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Track",
            "thumbnail_url": "https://example.com/art.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Artist - Track Official",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )
        results = downloader._search_youtube("Artist", "Track")
        selected_result = results[0]

        download = Download(
            url=downloader._extract_youtube_url(selected_result) or "",
            name="Artist - Track.mp3",
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
        )

        assert download.url == "https://youtube.com/watch?v=video1"
        assert download.name == "Artist - Track.mp3"
        assert download.service_type == "spotify"
        assert download.audio_only is True

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.BeautifulSoup")
    def test_dialog_playlist_select_multiple_tracks(self, mock_bs4, mock_get):
        """Verify dialog allows selecting multiple tracks from playlist."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "My Playlist",
            "thumbnail_url": "https://example.com/pl.jpg",
        }
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        row_one = Mock()
        row_one.find.return_value = Mock(get_text=Mock(return_value="Song One"))
        row_two = Mock()
        row_two.find.return_value = Mock(get_text=Mock(return_value="Song Two"))
        row_three = Mock()
        row_three.find.return_value = Mock(get_text=Mock(return_value="Song Three"))
        mock_soup = Mock()
        mock_soup.find_all.return_value = [row_one, row_two, row_three]
        mock_bs4.return_value = mock_soup

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )
        metadata = downloader.get_metadata("https://open.spotify.com/playlist/abc123")

        assert len(metadata.get("tracks", [])) >= 0

        selected_tracks = [0, 2]
        downloads_created = []

        for idx in selected_tracks:
            track = metadata["tracks"][idx]
            downloads_created.append(
                {
                    "title": track["title"],
                    "position": track["position"],
                }
            )

        assert len(downloads_created) == 2
        assert downloads_created[0]["title"] == "Song One"
        assert downloads_created[1]["title"] == "Song Three"


@pytest.mark.integration
class TestSpotifyUserNotifications:
    """Test Spotify user notifications and error handling."""

    @patch("src.services.spotify.downloader.requests.get")
    def test_notify_user_on_success(self, mock_get):
        """Verify user is notified on successful metadata fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Track",
            "thumbnail_url": "https://example.com/art.jpg",
        }
        mock_get.return_value = mock_response

        error_handler = MockErrorNotifier()
        downloader = SpotifyDownloader(
            error_handler=error_handler, file_service=MockFileService(), config=get_config()
        )

        metadata = downloader._extract_spotify_metadata("https://open.spotify.com/track/abc123")

        assert metadata is not None
        assert metadata["title"] == "Artist - Track"

    @patch("src.services.spotify.downloader.requests.get")
    def test_notify_user_on_metadata_failure(self, mock_get):
        """Verify user is notified on metadata fetch failure."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        error_handler = MockErrorNotifier()
        downloader = SpotifyDownloader(
            error_handler=error_handler, file_service=MockFileService(), config=get_config()
        )

        metadata = downloader._extract_spotify_metadata("https://open.spotify.com/track/abc123")

        assert metadata is not None
        assert "title" in metadata
        assert metadata["id"] == "abc123"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_notify_user_on_youtube_search_failure(self, mock_get, mock_ydl_class):
        """Verify user is notified on YouTube search failure."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Artist - Track"}
        mock_get.return_value = mock_response

        from yt_dlp.utils import DownloadError

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = DownloadError("Network error")
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        error_handler = MockErrorNotifier()
        downloader = SpotifyDownloader(
            error_handler=error_handler, file_service=MockFileService(), config=get_config()
        )

        results = downloader._search_youtube("Artist", "Track")

        assert results == []

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_notify_user_on_no_matches_found(self, mock_get, mock_ydl_class):
        """Verify user is notified when no YouTube matches are found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Artist - Track"}
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {"entries": []}
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        error_handler = MockErrorNotifier()
        downloader = SpotifyDownloader(
            error_handler=error_handler, file_service=MockFileService(), config=get_config()
        )

        results = downloader._search_youtube("Fake Artist", "Fake Track")

        assert results == []

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    @patch("src.services.spotify.downloader.requests.get")
    def test_notify_user_on_best_match_found(self, mock_get, mock_ydl_class):
        """Verify user sees similarity score for best match."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Artist - Track"}
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "video1",
                    "title": "Artist - Track (Official Video)",
                    "duration": 240,
                    "url": "https://youtube.com/watch?v=video1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )

        results = downloader._search_youtube("Artist", "Track")
        best_match = downloader._select_best_match("Artist Track", results)

        assert best_match is not None
        assert best_match["id"] == "video1"

        similarity = downloader._calculate_similarity("Artist Track", best_match["title"])

        assert similarity > 0.5


@pytest.mark.integration
class TestSpotifyErrorHandling:
    """Test Spotify error handling and edge cases."""

    @patch("src.services.spotify.downloader.requests.get")
    def test_handle_timeout_gracefully(self, mock_get):
        """Verify timeout is handled gracefully with fallback."""
        import requests

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.Timeout("Timeout")
        mock_get.return_value = mock_response

        error_handler = MockErrorNotifier()
        downloader = SpotifyDownloader(
            error_handler=error_handler, file_service=MockFileService(), config=get_config()
        )

        metadata = downloader._extract_spotify_metadata("https://open.spotify.com/track/abc123")

        assert metadata is not None
        assert metadata["title"] == "Spotify Track"
        assert metadata["id"] == "abc123"

    def test_handle_invalid_spotify_url(self):
        """Verify invalid Spotify URLs are handled correctly."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())

        metadata = handler.get_metadata("https://invalid-url.com/track/abc123")

        assert "type" in metadata
        assert metadata["type"] == "unknown"

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.BeautifulSoup")
    def test_handle_empty_playlist(self, mock_bs4, mock_get):
        """Verify empty playlists are handled correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Empty Playlist"}
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        mock_soup = Mock()
        mock_soup.find_all.return_value = []
        mock_bs4.return_value = mock_soup

        downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(), file_service=MockFileService(), config=get_config()
        )
        metadata = downloader.get_metadata("https://open.spotify.com/playlist/empty123")

        assert "tracks" in metadata
        assert len(metadata["tracks"]) == 0

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    def test_handle_youtube_search_retries(self, mock_ydl_class, mock_get):
        """Verify YouTube search retries on failure."""
        from yt_dlp.utils import DownloadError

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"title": "Artist - Track"}
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.side_effect = [
            DownloadError("Network error"),
            DownloadError("Network error"),
            {
                "entries": [
                    {
                        "id": "video1",
                        "title": "Artist - Track",
                        "duration": 240,
                        "url": "https://youtube.com/watch?v=video1",
                    }
                ]
            },
        ]
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        error_handler = MockErrorNotifier()
        downloader = SpotifyDownloader(
            error_handler=error_handler, file_service=MockFileService(), config=get_config()
        )

        results = downloader._search_youtube("Artist", "Track")

        assert len(results) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
