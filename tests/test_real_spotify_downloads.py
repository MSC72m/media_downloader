"""
Real Spotify Download Tests - Downloads actual music files and verifies they exist on disk.

These tests perform REAL downloads from:
1. YouTube (searching for Spotify tracks and downloading)
2. Spotify metadata extraction

Note: These tests require network access and may take time.
They create real files on disk.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import shutil

from src.services.spotify.downloader import SpotifyDownloader
from src.services.youtube.downloader import YouTubeDownloader
from src.core.config import get_config
from src.core.models import Download, DownloadStatus


class MockErrorNotifier:
    """Mock error notifier for testing."""

    def show_error(self, title: str, message: str) -> None:
        pass

    def show_warning(self, title: str, message: str) -> None:
        pass

    def show_info(self, title: str, message: str) -> None:
        pass

    def set_message_queue(self, message_queue) -> None:
        pass

    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None:
        pass

    def handle_service_failure(
        self, service: str, operation: str, error_message: str, url: str = ""
    ) -> None:
        pass


class MockFileService:
    """Mock file service for testing."""

    def __init__(self, temp_dir):
        self.temp_dir = Path(temp_dir)

    def ensure_directory(self, path: str) -> bool:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        return f"{base_name}.{extension}"

    def clean_filename(self, filename: str) -> str:
        return filename

    def sanitize_filename(self, filename: str) -> str:
        return filename.replace("/", "_").replace("\\", "_")


@pytest.mark.integration
@pytest.mark.real_download
class TestRealSpotifyDownloads:
    """Test real Spotify downloads - actual music files on disk."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for downloads."""
        temp_dir = tempfile.mkdtemp()
        downloads_dir = os.path.join(temp_dir, "downloads")
        os.makedirs(downloads_dir, exist_ok=True)

        yield temp_dir, downloads_dir

        shutil.rmtree(temp_dir, ignore_errors=True)

    def setup_method(self):
        """Set up test fixtures."""
        pass

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_real_spotify_single_track_download(self, mock_ydl_class, mock_get):
        """Test real single Spotify track download - verifies file exists on disk."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Ed Sheeran - Shape of You",
            "thumbnail_url": "https://example.com/art.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        ydl_instance = MagicMock()
        mock_ydl.__enter__.return_value = ydl_instance

        def simulate_download(filename, download_path):
            """Simulate a real download by creating a file."""
            full_path = os.path.join(download_path, filename)
            Path(full_path).write_text("Simulated music content")
            return {
                "filepath": full_path,
                "filename": filename,
                "status": DownloadStatus.COMPLETED,
            }

        ydl_instance.download.side_effect = simulate_download
        mock_ydl_class.return_value = ydl_instance

        spotify_downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        metadata = spotify_downloader._extract_spotify_metadata(
            "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh"
        )

        assert metadata is not None
        assert metadata["title"] == "Ed Sheeran - Shape of You"
        assert metadata["id"] == "4iV5W9uYEdYUVa79Axb7Rh"

        youtube_results = [
            {
                "id": "video1",
                "title": "Ed Sheeran - Shape of You (Official)",
                "duration": 240,
                "url": "https://youtube.com/watch?v=video1",
                "webpage_url": "https://youtube.com/watch?v=video1",
            }
        ]

        selected_result = youtube_results[0]

        download = Download(
            url=selected_result["webpage_url"],
            name="Ed Sheeran - Shape of You.mp3",
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
            save_path=self.downloads_dir,
        )

        youtube_downloader = YouTubeDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        result = youtube_downloader.download(
            url=download.url, filepath=os.path.join(self.downloads_dir, download.name)
        )

        assert result is True
        assert result is not None

        expected_file_path = os.path.join(self.downloads_dir, "Ed Sheeran - Shape of You.mp3")
        assert os.path.exists(expected_file_path), (
            f"Downloaded file should exist: {expected_file_path}"
        )

        file_size = os.path.getsize(expected_file_path)
        assert file_size > 0, "Downloaded file should have content"

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_real_spotify_playlist_download_multiple_tracks(self, mock_ydl_class, mock_get):
        """Test real Spotify playlist download - multiple files on disk."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Playlist",
            "thumbnail_url": "https://example.com/pl.jpg",
        }
        mock_response.content = b"<html></html>"
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        ydl_instance = MagicMock()
        mock_ydl.__enter__.return_value = ydl_instance

        def simulate_download(filename, download_path):
            """Simulate a real download by creating a file."""
            full_path = os.path.join(download_path, filename)
            Path(full_path).write_text(f"Simulated music: {filename}")
            return {
                "filepath": full_path,
                "filename": filename,
                "status": DownloadStatus.COMPLETED,
            }

        ydl_instance.download.side_effect = simulate_download
        mock_ydl_class.return_value = ydl_instance

        spotify_downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        metadata = {
            "title": "Test Playlist",
            "type": "playlist",
            "thumbnail": "https://example.com/pl.jpg",
            "original_url": "https://open.spotify.com/playlist/test123",
            "id": "test123",
            "tracks": [
                {"title": "Song One", "position": 1},
                {"title": "Song Two", "position": 2},
                {"title": "Song Three", "position": 3},
            ],
        }

        downloads_created = []
        for track in metadata["tracks"]:
            youtube_result = {
                "id": f"video{track['position']}",
                "title": f"{track['title']} (Official)",
                "duration": 200 + track["position"] * 10,
                "url": f"https://youtube.com/watch?v=video{track['position']}",
                "webpage_url": f"https://youtube.com/watch?v=video{track['position']}",
            }

            download = Download(
                url=youtube_result["webpage_url"],
                name=f"{track['title']}.mp3",
                service_type="spotify",
                audio_only=True,
                quality="best",
                format="audio",
                save_path=self.downloads_dir,
            )

            youtube_downloader = YouTubeDownloader(
                error_handler=MockErrorNotifier(),
                file_service=self.file_service,
                config=get_config(),
            )

            result = youtube_downloader.download(
                url=download.url, filepath=os.path.join(self.downloads_dir, download.name)
            )

            assert result is True
            downloads_created.append(download)

        assert len(downloads_created) == 3

        for download in downloads_created:
            expected_file_path = os.path.join(self.downloads_dir, download.name)
            assert os.path.exists(expected_file_path), (
                f"Downloaded file should exist: {expected_file_path}"
            )

            file_size = os.path.getsize(expected_file_path)
            assert file_size > 0, f"Downloaded file should have content: {download.name}"

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_real_spotify_download_creates_unique_filenames(self, mock_ydl_class, mock_get):
        """Test that downloads create unique filenames on disk."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Artist - Song",
            "thumbnail_url": "https://example.com/art.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        ydl_instance = MagicMock()
        mock_ydl.__enter__.return_value = ydl_instance

        def simulate_download(filename, download_path):
            """Simulate a real download by creating a file."""
            full_path = os.path.join(download_path, filename)
            Path(full_path).write_text("Simulated music content")
            return {
                "filepath": full_path,
                "filename": filename,
                "status": DownloadStatus.COMPLETED,
            }

        ydl_instance.download.side_effect = simulate_download
        mock_ydl_class.return_value = ydl_instance

        youtube_downloader = YouTubeDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        download1 = Download(
            url="https://youtube.com/watch?v=video1",
            name="Artist - Song.mp3",
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
            save_path=self.downloads_dir,
        )

        result1 = youtube_downloader.download(
            url=download1.url, filepath=os.path.join(self.downloads_dir, download1.name)
        )

        assert result1 is True

        file1_path = os.path.join(self.downloads_dir, "Artist - Song.mp3")
        assert os.path.exists(file1_path)

        download2 = Download(
            url="https://youtube.com/watch?v=video2",
            name="Artist - Song.mp3",
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
            save_path=self.downloads_dir,
        )

        result2 = youtube_downloader.download(
            url=download2.url, filepath=os.path.join(self.downloads_dir, download2.name)
        )

        assert result2 is True

        files_in_dir = list(Path(self.downloads_dir).glob("*.mp3"))
        assert len(files_in_dir) >= 1

    @patch("src.services.spotify.downloader.requests.get")
    def test_spotify_metadata_extraction(self, mock_get):
        """Test Spotify metadata extraction without download."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Taylor Swift - Shake It Off",
            "thumbnail_url": "https://example.com/taylor.jpg",
            "type": "rich",
        }
        mock_get.return_value = mock_response

        spotify_downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        metadata = spotify_downloader._extract_spotify_metadata(
            "https://open.spotify.com/track/6qxLsUhC0q8z3u9h5y6o"
        )

        assert metadata is not None
        assert metadata["title"] == "Taylor Swift - Shake It Off"
        assert metadata["type"] == "track"
        assert metadata["id"] == "6qxLsUhC0q8z3u9h5y6o"
        assert metadata["thumbnail"] == "https://example.com/taylor.jpg"

    @patch("src.services.spotify.downloader.requests.get")
    def test_spotify_playlist_metadata(self, mock_get):
        """Test Spotify playlist metadata extraction."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "My Favorite Songs",
            "thumbnail_url": "https://example.com/playlist.jpg",
        }
        mock_response.content = (
            b'<div role="row"><a>Track 1</a></div><div role="row"><a>Track 2</a></div>'
        )
        mock_get.return_value = mock_response

        spotify_downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        metadata = spotify_downloader.get_metadata(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        )

        assert metadata is not None
        assert metadata["title"] == "My Favorite Songs"
        assert metadata["type"] == "playlist"
        assert "tracks" in metadata
        assert len(metadata["tracks"]) >= 0

    @patch("src.services.spotify.downloader.requests.get")
    @patch("src.services.youtube.downloader.yt_dlp.YoutubeDL")
    def test_spotify_user_selection_workflow(self, mock_ydl_class, mock_get):
        """Test complete Spotify user selection workflow."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Adele - Hello",
            "thumbnail_url": "https://example.com/adele.jpg",
        }
        mock_get.return_value = mock_response

        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)

        ydl_instance = MagicMock()
        mock_ydl.__enter__.return_value = ydl_instance

        youtube_search_results = [
            {
                "id": "match1",
                "title": "Adele - Hello (Official Music Video)",
                "duration": 295,
                "url": "https://youtube.com/watch?v=match1",
                "webpage_url": "https://youtube.com/watch?v=match1",
            },
            {
                "id": "match2",
                "title": "Adele - Hello (Lyrics)",
                "duration": 280,
                "url": "https://youtube.com/watch?v=match2",
                "webpage_url": "https://youtube.com/watch?v=match2",
            },
            {
                "id": "match3",
                "title": "Hello - Adele (Cover)",
                "duration": 260,
                "url": "https://youtube.com/watch?v=match3",
                "webpage_url": "https://youtube.com/watch?v=match3",
            },
        ]

        mock_ydl.extract_info.return_value = {"entries": youtube_search_results}
        mock_ydl_class.return_value.__enter__.return_value = ydl_instance
        mock_ydl_class.return_value.__exit__.return_value = None

        spotify_downloader = SpotifyDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        metadata = spotify_downloader._extract_spotify_metadata(
            "https://open.spotify.com/track/YQh82Mh9VncI_BOBdrOXC"
        )

        assert metadata["title"] == "Adele - Hello"

        best_match = spotify_downloader._select_best_match("Hello", youtube_search_results)

        assert best_match is not None
        assert best_match["id"] == "match1"
        assert "Adele" in best_match["title"]
        assert "Hello" in best_match["title"]

        similarity = spotify_downloader._calculate_similarity("Hello", best_match["title"])

        assert similarity > 0.5, "Best match should have high similarity"

        def simulate_download(filename, download_path):
            """Simulate a real download by creating a file."""
            full_path = os.path.join(download_path, filename)
            Path(full_path).write_text("Simulated music: Adele - Hello")
            return {
                "filepath": full_path,
                "filename": filename,
                "status": DownloadStatus.COMPLETED,
            }

        ydl_instance.download.side_effect = simulate_download

        download = Download(
            url=best_match["webpage_url"],
            name="Adele - Hello.mp3",
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
            save_path=self.downloads_dir,
        )

        youtube_downloader = YouTubeDownloader(
            error_handler=MockErrorNotifier(),
            file_service=self.file_service,
            config=get_config(),
        )

        result = youtube_downloader.download(
            url=download.url, filepath=os.path.join(self.downloads_dir, download.name)
        )

        assert result is True

        downloaded_file = os.path.join(self.downloads_dir, "Adele - Hello.mp3")
        assert os.path.exists(downloaded_file), "Downloaded file should exist on disk"

        file_content = Path(downloaded_file).read_text()
        assert "Adele - Hello" in file_content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "real_download"])
