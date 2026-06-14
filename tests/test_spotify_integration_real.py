"""
Integration tests for Spotify downloader with real Spotify URLs.

These tests require network access and may fail if:
- Spotify OEmbed API is unavailable (currently experiencing 504 Gateway Timeout)
- YouTube search is blocked by network/firewall
- Network connection is unstable

To run these tests, ensure you have:
1. Active internet connection
2. No firewall blocking Spotify/YouTube APIs
3. Python environment with yt-dlp and requests installed
"""

import pytest

from src.services.spotify.downloader import SpotifyDownloader
from src.core.config import get_config


@pytest.mark.integration
class TestSpotifyRealDownloads:
    """Test Spotify downloader with real Spotify URLs."""

    def setup_method(self):
        """Set up test fixtures."""
        self.downloader = SpotifyDownloader(error_handler=None, config=get_config())

    @pytest.mark.skipif(
        True, reason="Spotify OEmbed API is experiencing 504 Gateway Timeout issues"
    )
    def test_extract_metadata_from_real_track(self):
        """Test metadata extraction from a real Spotify track URL."""
        url = "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9L"
        metadata = self.downloader._extract_spotify_metadata(url)

        assert metadata is not None
        assert "title" in metadata
        assert "type" in metadata
        assert metadata["type"] == "track"
        assert "id" in metadata
        print(f"Metadata: {metadata}")

    @pytest.mark.skipif(
        True, reason="Spotify OEmbed API is experiencing 504 Gateway Timeout issues"
    )
    def test_extract_metadata_from_real_playlist(self):
        """Test metadata extraction from a real Spotify playlist URL."""
        url = "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        metadata = self.downloader._extract_spotify_metadata(url)

        assert metadata is not None
        assert "title" in metadata
        assert "type" in metadata
        assert metadata["type"] == "playlist"
        assert "id" in metadata
        print(f"Metadata: {metadata}")

    @pytest.mark.skipif(True, reason="YouTube search requires internet and may be blocked")
    def test_youtube_search_for_real_song(self):
        """Test YouTube search for a well-known song."""
        results = self.downloader._search_youtube("Ed Sheeran", "Shape of You")

        assert isinstance(results, list)
        if len(results) > 0:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results[:3]):
                print(f"  {i + 1}. {result.get('title')}")
        else:
            print("No results found (network issue)")

    def test_similarity_scoring(self):
        """Test similarity scoring with real song titles."""
        spotify_title = "Shape of You"

        youtube_titles = [
            "Ed Sheeran - Shape of You (Official Music Video)",
            "Shape of You - Ed Sheeran (Lyrics)",
            "Completely Different Song Title",
        ]

        for yt_title in youtube_titles:
            score = self.downloader._calculate_similarity(spotify_title, yt_title)
            print(f"Similarity score for '{yt_title}': {score:.2f}")
            assert 0.0 <= score <= 1.0

    @pytest.mark.skipif(True, reason="Requires full end-to-end test with network access")
    def test_full_track_download_workflow(self):
        """Test complete workflow for a Spotify track."""
        # This is a manual test that shows the workflow
        print("\n=== Spotify Track Download Workflow ===")
        print("1. Spotify URL provided by user")
        print("2. Extract track ID and basic info")
        print("3. Search YouTube for matching videos")
        print("4. Show results to user for selection")
        print("5. Download selected video from YouTube as audio")
        print("\nNote: This workflow doesn't require Spotify credentials.")
        print("      Downloads happen from YouTube after user selects match.")

    @pytest.mark.skipif(True, reason="Requires real Spotify playlist with public access")
    def test_playlist_scrape_workflow(self):
        """Test playlist scraping workflow."""
        print("\n=== Spotify Playlist Download Workflow ===")
        print("1. Extract playlist ID from URL")
        print("2. Attempt to scrape track list from Spotify page")
        print("3. For each track:")
        print("   a. Search YouTube for matching video")
        print("   b. Show match to user")
        print("   c. Download selected video as audio")
        print("\nNote: Playlist scraping may be blocked by Spotify.")
        print("      Alternative: User manually enters track list.")


@pytest.mark.integration
class TestSpotifyNetworkIssues:
    """Test handling of network issues."""

    def setup_method(self):
        """Set up test fixtures."""
        self.downloader = SpotifyDownloader(error_handler=None, config=get_config())

    def test_metadata_fallback_on_timeout(self):
        """Test that metadata extraction returns fallback on timeout."""
        url = "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9L"

        metadata = self.downloader._extract_spotify_metadata(url)

        assert metadata is not None
        assert "id" in metadata
        assert metadata["id"] == "3n3Ppam7vgaVa1iaRUc9L"
        # Fallback metadata should have basic info
        assert "title" in metadata
        assert "type" in metadata

    def test_youtube_search_returns_empty_on_failure(self):
        """Test that YouTube search returns empty list on failure."""
        # Using a fake song that likely won't be found
        # and handles network errors
        results = self.downloader._search_youtube("FakeArtist123", "FakeSong456")

        assert isinstance(results, list)
        print(f"Search returned {len(results)} results")

    def test_similarity_calculation_always_works(self):
        """Test that similarity calculation works even without network."""
        score = self.downloader._calculate_similarity("Song Title", "Different Title")

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
        print(f"Similarity score: {score:.2f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
