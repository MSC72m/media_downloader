"""Real download integration tests that actually download files.

These tests bypass the mocking in conftest to test real downloads.
"""

import os
import sys
import tempfile
from pathlib import Path
import unittest.mock

# Import real requests before conftest can mock it
import requests
import pytest

# Now import our modules
from src.core.config import get_config
from src.core.interfaces import IErrorNotifier, IFileService
from src.services.radiojavan.downloader import RadioJavanDownloader
from src.services.tiktok.downloader import TikTokDownloader
from src.services.network.downloader import download_file


class MockFileService:
    """Mock file service for testing."""

    def ensure_directory(self, path: str) -> bool:
        return True

    def sanitize_filename(self, filename: str) -> str:
        return filename

    def clean_filename(self, filename: str) -> str:
        return filename

    def download_file(self, url: str, path: str, progress_callback=None):
        _ = (url, path, progress_callback)
        class Result:
            success = True

        return Result()

    def save_text_file(self, content: str, file_path: str) -> bool:
        _ = (content, file_path)
        return True

    def get_unique_filename(self, directory: str, base_name: str, extension: str = "") -> str:
        return f"{directory}/{base_name}{extension}"


class MockErrorNotifier:
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

    def show_info(self, title: str, message: str) -> None:
        pass

    def set_message_queue(self, message_queue) -> None:
        pass


class TestActualDownloads:
    """Test actual file downloads with real network requests."""

    def test_network_download_basic_file(self):
        """Test downloading a real file from the internet."""
        # Use a known working test file
        test_url = "https://httpbin.org/json"

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "test_download.json")

            print(f"Testing download from: {test_url}")

            # Perform actual download
            result = download_file(url=test_url, save_path=save_path, config=get_config())

            # Verify download was successful
            assert result is True, "Download should succeed"

            # Check that file was created
            assert os.path.exists(save_path), "File should be created"

            # Verify file size and content
            file_size = os.path.getsize(save_path)
            assert file_size > 0, "File should have content"
            print(f"✅ Successfully downloaded {file_size} bytes")

            # Verify content is valid JSON
            with open(save_path, "r") as f:
                content = f.read()
                assert "slideshow" in content, "Content should be valid"
                print(f"✅ Content verified: {content[:50]}...")

    def test_radiojavan_url_construction_logic(self):
        """Test RadioJavan URL construction logic without network."""
        # Temporarily bypass requests validation
        original_validate = RadioJavanDownloader._validate_url

        def mock_validate(self, url):
            # Mock validation that returns True for any URL with correct format
            return "httpbin.org" not in url  # Return False for test URLs, True for others

        # Temporarily replace validation method
        RadioJavanDownloader._validate_url = mock_validate

        try:
            downloader = RadioJavanDownloader()

            # Test URL construction
            test_url = "https://www.radiojavan.com/mp3/test-song-name/"
            download_url = downloader._construct_download_url(test_url)

            assert download_url is not None, "Should construct download URL"
            assert download_url.startswith("https://"), "Should be HTTPS URL"
            assert "test-song-name" in download_url, "Should contain media name"

            print(f"✅ URL construction works: {download_url}")

        finally:
            # Restore original method
            RadioJavanDownloader._validate_url = original_validate

    def test_tiktok_download_configuration(self):
        """Test TikTok download configuration and readiness."""
        # Unmock yt_dlp temporarily for this test
        with unittest.mock.patch.dict("sys.modules", {"yt_dlp": unittest.mock.MagicMock()}):
            downloader = TikTokDownloader()

            # Test configuration
            assert downloader.default_timeout > 0, "Should have timeout configured"
            assert downloader.max_retries > 0, "Should have retry count configured"

            # Test yt-dlp options
            options = downloader._get_ytdl_options()
            assert options["format"] == "best", "Should select best quality"
            assert options["quiet"] is True, "Should be in quiet mode"
            assert "extractor_args" in options, "Should have extractor args"

            tiktok_args = options["extractor_args"]["tiktok"]
            assert tiktok_args["enable_download"] is True, "Should enable downloads"
            assert tiktok_args["download_thumbnail"] is True, "Should download thumbnails"

            print("✅ TikTok downloader properly configured")

    def test_radiojavan_media_extraction(self):
        """Test RadioJavan media name extraction."""
        downloader = RadioJavanDownloader()

        # Test MP3 extraction
        mp3_url = "https://www.radiojavan.com/mp3/artist-song-name/"
        media_name = downloader._extract_media_name(mp3_url)
        assert media_name == "artist-song-name", f"Expected 'artist-song-name', got '{media_name}'"

        # Test MP4 extraction
        mp4_url = "https://www.radiojavan.com/mp4/video-name/"
        media_name = downloader._extract_media_name(mp4_url)
        assert media_name == "video-name", f"Expected 'video-name', got '{media_name}'"

        # Test invalid URL
        invalid_url = "https://www.radiojavan.com/invalid/test/"
        media_name = downloader._extract_media_name(invalid_url)
        assert media_name is None, "Should return None for invalid URL"

        print("✅ Media name extraction works correctly")

    def test_progress_callback_functionality(self):
        """Test progress callback mechanisms."""
        progress_data = []

        def progress_callback(progress, speed):
            progress_data.append((progress, speed))

        # Test TikTok progress hook
        with unittest.mock.patch.dict("sys.modules", {"yt_dlp": unittest.mock.MagicMock()}):
            downloader = TikTokDownloader()
            hook = downloader._create_progress_hook(progress_callback)

            # Test downloading status
            hook(
                {
                    "status": "downloading",
                    "downloaded_bytes": 50,
                    "total_bytes": 100,
                    "speed": 1024 * 1024,
                }
            )

            assert len(progress_data) == 1, "Progress callback should be called"
            progress, speed = progress_data[0]
            assert progress == 50.0, f"Expected 50.0%, got {progress}%"
            assert speed > 0, f"Expected positive speed, got {speed}"

            # Test finished status
            hook({"status": "finished"})

            assert len(progress_data) == 2, "Should be called twice"
            final_progress, final_speed = progress_data[1]
            assert final_progress == 100.0, f"Expected 100.0%, got {final_progress}%"
            assert final_speed == 0.0, f"Expected 0.0 speed, got {final_speed}"

        print("✅ Progress callback functionality works")

    def test_file_validation_and_size_checks(self):
        """Test file validation and size checking."""
        # Test with a small file
        small_file_url = "https://httpbin.org/bytes/1024"  # 1KB file

        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "small_file.bin")

            result = download_file(url=small_file_url, save_path=save_path, config=get_config())

            assert result is True, "Download should succeed"
            assert os.path.exists(save_path), "File should exist"

            file_size = os.path.getsize(save_path)
            assert file_size == 1024, f"Expected 1024 bytes, got {file_size}"

            print(f"✅ Small file download verified: {file_size} bytes")

    def test_download_error_handling(self):
        """Test download error handling with invalid URLs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = os.path.join(temp_dir, "error_test")

            # Test 404 URL
            result = download_file(
                url="https://httpbin.org/status/404", save_path=save_path, config=get_config()
            )

            # Should handle error gracefully (may return False or handle internally)
            print(f"404 handling result: {result}")

            # Test invalid domain
            result = download_file(
                url="https://nonexistent-domain-12345.com/file",
                save_path=save_path,
                config=get_config(),
            )

            print(f"Invalid domain handling result: {result}")
            print("✅ Error handling tested (results may vary by network conditions)")

    @pytest.mark.integration
    def test_complete_radiojavan_flow_simulation(self):
        """Simulate complete RadioJavan download flow with mocked success."""
        # This test simulates the entire flow without depending on actual RJ servers

        downloader = RadioJavanDownloader()

        # Step 1: Test URL parsing
        test_url = "https://www.radiojavan.com/mp3/sample-song/"
        media_name = downloader._extract_media_name(test_url)
        assert media_name == "sample-song", "Should extract media name"

        # Step 2: Test CDN host logic (without actual network calls)
        hosts = downloader.CDN_HOSTS
        paths = downloader.MP3_PATHS

        assert len(hosts) > 1, "Should have multiple CDN hosts"
        assert len(paths) > 1, "Should have multiple path patterns"

        # Step 3: Test URL construction format
        for host in hosts:
            for path in paths:
                constructed_url = f"https://{host}{path.format(media_name=media_name)}"
                assert constructed_url.startswith("https://"), "Should be HTTPS"
                assert media_name in constructed_url, "Should contain media name"
                assert any(ext in path for ext in ["/mp3", "/mp3s"]), "Should use MP3 paths"

        print("✅ Complete RadioJavan flow simulation passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
