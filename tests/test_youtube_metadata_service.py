"""Unit tests for YouTube metadata service."""

import pytest
import sys
import os
import subprocess
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestYouTubeMetadataService:
    """Test cases for YouTubeMetadataService."""

    @pytest.fixture
    def mock_youtube_metadata(self):
        """Mock YouTube metadata for testing."""
        return {
            'title': 'Test Video',
            'duration': 180,
            'view_count': 1000000,
            'upload_date': '20230101',
            'channel': 'Test Channel',
            'description': 'Test description',
            'thumbnail': 'http://example.com/thumb.jpg',
            'subtitles': {},
            'automatic_captions': {}
        }

    @pytest.fixture
    def mock_subprocess_result(self):
        """Mock subprocess result for testing."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test Video\n180\n1000000\n20230101\nTest Channel\nTest description\nhttp://example.com/thumb.jpg"
        mock_result.stderr = ""
        return mock_result

    @pytest.fixture
    def mock_subprocess_error(self):
        """Mock subprocess error for testing."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ERROR: Test error"
        return mock_result

    def test_fetch_metadata_with_no_cookies(self, mock_subprocess_result, mock_youtube_metadata):
        """Test metadata fetch without cookies."""
        with patch('subprocess.run', return_value=mock_subprocess_result):
            # Import here to avoid import issues
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123')

            assert metadata is not None
            assert metadata.title == 'Test Video'
            assert metadata.duration == '3:00'
            assert metadata.channel == 'Test Channel'
            assert metadata.error is None

    def test_fetch_metadata_with_chrome_browser(self, mock_subprocess_result, mock_youtube_metadata):
        """Test metadata fetch with Chrome browser cookies."""
        with patch('subprocess.run', return_value=mock_subprocess_result):
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123', browser='chrome')

            assert metadata is not None
            assert metadata.title == 'Test Video'
            assert metadata.duration == '3:00'
            assert metadata.channel == 'Test Channel'

    def test_fetch_metadata_with_firefox_browser(self, mock_subprocess_result, mock_youtube_metadata):
        """Test metadata fetch with Firefox browser cookies."""
        with patch('subprocess.run', return_value=mock_subprocess_result):
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123', browser='firefox')

            assert metadata is not None
            assert metadata.title == 'Test Video'
            assert metadata.duration == '3:00'
            assert metadata.channel == 'Test Channel'

    def test_fetch_metadata_with_safari_browser(self, mock_subprocess_result, mock_youtube_metadata):
        """Test metadata fetch with Safari browser cookies."""
        with patch('subprocess.run', return_value=mock_subprocess_result):
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123', browser='safari')

            assert metadata is not None
            assert metadata.title == 'Test Video'
            assert metadata.duration == '3:00'
            assert metadata.channel == 'Test Channel'

    def test_fetch_metadata_with_manual_cookie_file(self, mock_subprocess_result, mock_youtube_metadata, tmp_path):
        """Test metadata fetch with manual cookie file."""
        with patch('subprocess.run', return_value=mock_subprocess_result):
            from services.youtube.metadata_service import YouTubeMetadataService

            # Create a temporary cookie file
            cookie_file = tmp_path / "cookies.txt"
            cookie_file.write_text("# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tFALSE\t1234567890\ttest\tvalue")

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123', cookie_path=str(cookie_file))

            assert metadata is not None
            assert metadata.title == 'Test Video'
            assert metadata.duration == '3:00'
            assert metadata.channel == 'Test Channel'

    def test_fetch_metadata_with_browser_and_cookie_path_priority(self, mock_subprocess_result, mock_youtube_metadata):
        """Test that browser parameter takes priority over cookie_path."""
        with patch('subprocess.run', return_value=mock_subprocess_result) as mock_run:
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata(
                'https://www.youtube.com/watch?v=test123',
                cookie_path='/some/cookie/path',
                browser='chrome'
            )

            assert metadata is not None
            assert metadata.title == 'Test Video'
            # Verify that subprocess was called with browser parameter, not cookie file
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert '--cookies-from-browser' in call_args
            assert 'chrome' in call_args
            assert '--cookies' not in call_args

    def test_fetch_metadata_with_invalid_url(self):
        """Test metadata fetch with invalid URL."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()
        metadata = service.fetch_metadata('https://example.com/not-youtube')

        assert metadata is not None
        assert metadata.error == "Invalid YouTube URL"

    def test_fetch_metadata_with_subprocess_error(self, mock_subprocess_error):
        """Test metadata fetch when subprocess fails."""
        with patch('subprocess.run', return_value=mock_subprocess_error):
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123')

            assert metadata is not None
            assert "Failed to fetch metadata" in metadata.error

    def test_fetch_metadata_with_timeout_error(self):
        """Test metadata fetch when subprocess times out."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired(cmd=['test'], timeout=60)):
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123')

            assert metadata is not None
            assert "Failed to fetch metadata" in metadata.error

    def test_validate_url(self):
        """Test URL validation."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Valid URLs
        assert service.validate_url('https://www.youtube.com/watch?v=test123') == True
        assert service.validate_url('https://youtu.be/test123') == True
        assert service.validate_url('https://youtube.com/watch?v=test123') == True
        assert service.validate_url('https://www.youtube.com/embed/test123') == True
        assert service.validate_url('https://www.youtube.com/v/test123') == True
        assert service.validate_url('https://www.youtube.com/playlist?list=test123') == True

        # Invalid URLs
        assert service.validate_url('https://example.com/watch?v=test123') == False
        assert service.validate_url('not-a-url') == False
        assert service.validate_url('') == False

    def test_extract_video_id(self):
        """Test video ID extraction."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Test various YouTube URL formats
        assert service.extract_video_id('https://www.youtube.com/watch?v=test123') == 'test123'
        assert service.extract_video_id('https://youtu.be/test123') == 'test123'
        assert service.extract_video_id('https://youtube.com/watch?v=test123') == 'test123'
        assert service.extract_video_id('https://www.youtube.com/embed/test123') == 'test123'
        assert service.extract_video_id('https://www.youtube.com/v/test123') == 'test123'

        # Test invalid URLs
        assert service.extract_video_id('https://example.com/watch?v=test123') is None
        assert service.extract_video_id('not-a-url') is None

    def test_format_duration(self):
        """Test duration formatting."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Test various durations
        assert service._format_duration(0) == "Unknown"
        assert service._format_duration(30) == "0:30"
        assert service._format_duration(90) == "1:30"
        assert service._format_duration(3661) == "1:01:01"
        assert service._format_duration(None) == "Unknown"

    def test_format_view_count(self):
        """Test view count formatting."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Test various view counts
        assert service._format_view_count(0) == "0 views"
        assert service._format_view_count(500) == "500 views"
        assert service._format_view_count(1500) == "1.5K views"
        assert service._format_view_count(1500000) == "1.5M views"
        assert service._format_view_count(None) == "0 views"

    def test_format_upload_date(self):
        """Test upload date formatting."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Test various upload dates
        assert service._format_upload_date('20230101') == "01/01/2023"
        assert service._format_upload_date('') == "Unknown date"
        assert service._format_upload_date('invalid') == "Unknown date"
        assert service._format_upload_date(None) == "Unknown date"

    def test_extract_qualities(self):
        """Test quality extraction."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        qualities = service._extract_qualities({})

        assert isinstance(qualities, list)
        assert '144p' in qualities
        assert '720p' in qualities
        assert '1080p' in qualities
        assert '4K' in qualities

    def test_extract_formats(self):
        """Test format extraction."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        formats = service._extract_formats({})

        assert isinstance(formats, list)
        assert 'video_only' in formats
        assert 'video_audio' in formats
        assert 'audio_only' in formats
        assert 'separate' in formats

    def test_extract_subtitles(self):
        """Test subtitle extraction."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Test with no subtitles
        info = {}
        subtitles = service._extract_subtitles(info)

        assert isinstance(subtitles, list)
        assert len(subtitles) == 1  # Only "None" option
        assert subtitles[0]['language_code'] == 'none'

    def test_get_language_name(self):
        """Test language name conversion."""
        from services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        # Test known languages
        assert service._get_language_name('en') == 'English'
        assert service._get_language_name('es') == 'Spanish'
        assert service._get_language_name('fr') == 'French'

        # Test unknown languages
        assert service._get_language_name('unknown') == 'unknown'
        assert service._get_language_name('en-US') == 'English'  # Test with dialect

    def test_fallback_without_cookies(self, mock_subprocess_result, mock_subprocess_error):
        """Test fallback behavior when cookies fail."""
        # First call fails (with cookies), second call succeeds (without cookies)
        with patch('subprocess.run', side_effect=[mock_subprocess_error, mock_subprocess_result]):
            from services.youtube.metadata_service import YouTubeMetadataService

            service = YouTubeMetadataService()
            metadata = service.fetch_metadata('https://www.youtube.com/watch?v=test123', browser='chrome')

            assert metadata is not None
            assert metadata.title == 'Test Video'
            assert metadata.duration == '3:00'