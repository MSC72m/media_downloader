"""Spotify integration-style tests with deterministic mocks."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.config import get_config
from src.services.spotify.downloader import SpotifyDownloader


class MockErrorNotifier:
    def show_error(self, title: str, message: str) -> None:
        _ = (title, message)

    def show_warning(self, title: str, message: str) -> None:
        _ = (title, message)

    def show_info(self, title: str, message: str) -> None:
        _ = (title, message)

    def set_message_queue(self, message_queue) -> None:
        _ = message_queue

    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None:
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
    def __init__(self, base: Path):
        self.base = base

    def ensure_directory(self, path: str) -> bool:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        suffix = extension if extension.startswith(".") else f".{extension}" if extension else ""
        return str(Path(directory) / f"{base_name}{suffix}")

    def clean_filename(self, filename: str) -> str:
        return filename

    def sanitize_filename(self, filename: str) -> str:
        return filename.replace("/", "_").replace("\\", "_")


@pytest.mark.integration
class TestRealSpotifyDownloads:
    @pytest.fixture
    def spotify_downloader(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_service = MockFileService(Path(tmp))
            yield SpotifyDownloader(
                error_handler=MockErrorNotifier(),
                file_service=file_service,
                config=get_config(),
            )

    @patch("src.services.spotify.downloader.requests.get")
    def test_spotify_track_metadata_extraction(self, mock_get, spotify_downloader: SpotifyDownloader):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "title": "Taylor Swift - Shake It Off",
            "thumbnail_url": "https://example.com/taylor.jpg",
            "type": "rich",
        }
        mock_get.return_value = mock_response

        metadata = spotify_downloader._extract_spotify_metadata(
            "https://open.spotify.com/track/6qxLsUhC0q8z3u9h5y6o"
        )

        assert metadata["title"] == "Taylor Swift - Shake It Off"
        assert metadata["type"] == "track"
        assert metadata["id"] == "6qxLsUhC0q8z3u9h5y6o"
        assert metadata["thumbnail"] == "https://example.com/taylor.jpg"

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.BeautifulSoup")
    def test_spotify_playlist_metadata_extraction(
        self,
        mock_bs4,
        mock_get,
        spotify_downloader: SpotifyDownloader,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "title": "My Favorite Songs",
            "thumbnail_url": "https://example.com/playlist.jpg",
        }
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        row_one = Mock()
        row_one.find.return_value = Mock(get_text=Mock(return_value="Track 1"))
        row_two = Mock()
        row_two.find.return_value = Mock(get_text=Mock(return_value="Track 2"))
        mock_soup = Mock()
        mock_soup.find_all.return_value = [row_one, row_two]
        mock_bs4.return_value = mock_soup

        metadata = spotify_downloader.get_metadata(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        )

        assert metadata["title"] == "My Favorite Songs"
        assert metadata["type"] == "playlist"
        assert "tracks" in metadata
        assert len(metadata["tracks"]) == 2
        assert metadata["tracks"][0]["title"] == "Track 1"

    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    def test_spotify_search_and_best_match(self, mock_ydl_class, spotify_downloader: SpotifyDownloader):
        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "match1",
                    "title": "Adele - Hello (Official Music Video)",
                    "duration": 295,
                    "url": "https://youtube.com/watch?v=match1",
                },
                {
                    "id": "match2",
                    "title": "Adele - Hello (Lyrics)",
                    "duration": 280,
                    "url": "https://youtube.com/watch?v=match2",
                },
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        results = spotify_downloader._search_youtube("Adele", "Hello")
        best_match = spotify_downloader._select_best_match("Adele Hello", results)

        assert len(results) == 2
        assert best_match is not None
        assert best_match["id"] == "match1"

    @patch("src.services.spotify.downloader.YouTubeDownloader")
    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.spotify.downloader.yt_dlp.YoutubeDL")
    def test_spotify_download_delegates_to_youtube_downloader(
        self,
        mock_ydl_class,
        mock_get,
        mock_youtube_downloader,
        spotify_downloader: SpotifyDownloader,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "title": "Adele - Hello",
            "thumbnail_url": "https://example.com/adele.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.extract_info.return_value = {
            "entries": [
                {
                    "id": "match1",
                    "title": "Adele - Hello (Official Music Video)",
                    "duration": 295,
                    "url": "https://youtube.com/watch?v=match1",
                }
            ]
        }
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl_class.return_value.__exit__.return_value = None

        mock_instance = Mock()
        mock_instance.download.return_value = True
        mock_youtube_downloader.return_value = mock_instance

        result = spotify_downloader.download(
            "https://open.spotify.com/track/YQh82Mh9VncI_BOBdrOXC",
            "/tmp/adele-hello.mp3",
        )

        assert result is True
        mock_instance.download.assert_called_once()
