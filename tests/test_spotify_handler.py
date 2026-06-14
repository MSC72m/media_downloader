import pytest

from src.handlers.spotify_handler import SpotifyHandler
from src.core.config import get_config


class MockMessageQueue:
    """Mock message queue for testing."""

    def add_message(self, message):
        pass

    def send_message(self, message):
        pass

    def register_handler(self, message_type, handler):
        pass


class TestSpotifyHandler:
    """Test Spotify handler functionality."""

    def test_get_patterns(self):
        """Test URL patterns."""
        patterns = SpotifyHandler.get_patterns()
        assert len(patterns) > 0
        assert any("spotify\\.com/track" in p for p in patterns)

    def test_detect_track_url(self):
        """Test track URL detection."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("https://open.spotify.com/track/abc123")
        assert url_type == "track"

    def test_detect_playlist_url(self):
        """Test playlist URL detection."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("https://open.spotify.com/playlist/def456")
        assert url_type == "playlist"

    def test_detect_album_url(self):
        """Test album URL detection."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("https://open.spotify.com/album/xyz789")
        assert url_type == "album"

    def test_detect_artist_url(self):
        """Test artist URL detection."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("https://open.spotify.com/artist/artist123")
        assert url_type == "artist"

    def test_extract_id(self):
        """Test ID extraction."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        track_id = handler._extract_spotify_id("https://open.spotify.com/track/abc123")
        assert track_id == "abc123"

    def test_uri_format_detection(self):
        """Test URI format detection."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("spotify:track:abc123")
        assert url_type == "unknown"

    def test_short_url_detection(self):
        """Test short URL detection."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("https://spotify.link/abc123")
        assert url_type == "unknown"

    def test_get_metadata(self):
        """Test metadata extraction."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        metadata = handler.get_metadata("https://open.spotify.com/track/abc123")

        assert "type" in metadata
        assert "id" in metadata
        assert metadata["requires_auth"] is False

    def test_unknown_url_type(self):
        """Test unknown URL type."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        url_type = handler._detect_spotify_type("https://example.com/video/123")
        assert url_type == "unknown"

    def test_get_metadata_invalid_id(self):
        """Test metadata extraction with invalid URL."""
        handler = SpotifyHandler(message_queue=MockMessageQueue())
        metadata = handler._extract_spotify_id("https://open.spotify.com/invalid")

        assert metadata is None
