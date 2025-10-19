"""Test UTF-8 subprocess handling fix for encoding issues."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.service_controller import ServiceController
try:
    from services.youtube.metadata_service import YouTubeMetadataService
except ImportError:
    # Use mock for testing
    class YouTubeMetadataService:
        def _get_basic_video_info(self, url):
            return None


class TestUTF8SubprocessHandling:
    """Test class for UTF-8 subprocess handling fixes."""

    @pytest.mark.skip(reason="Test expects subprocess calls but ServiceController uses yt-dlp Python API")
    def test_service_controller_encoding_environment(self):
        """Test that ServiceController sets proper encoding environment variables."""
        controller = ServiceController(Mock(), Mock())
        
        # Mock subprocess.run to capture environment
        with patch('core.service_controller.subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Success"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result
            
            # Create a mock download
            download = Mock()
            download.name = "Test Video with Special Characters: §°³"
            download.url = "https://youtube.com/watch?v=test"
            download.quality = "720p"
            download.output_path = "~/Downloads"
            download.audio_only = False
            download.download_playlist = False
            download.download_subtitles = False
            download.selected_subtitles = []
            download.download_thumbnail = True
            download.embed_metadata = True
            download.cookie_path = None
            download.selected_browser = None
            
            # Call the download worker
            controller._download_worker(download, "~/Downloads", None, None)
            
            # Verify subprocess was called with proper environment
            mock_subprocess.assert_called_once()
            call_kwargs = mock_subprocess.call_args[1]
            
            assert 'env' in call_kwargs, "subprocess.run should be called with env parameter"
            env = call_kwargs['env']
            
            # Check critical encoding environment variables
            assert env['PYTHONIOENCODING'] == 'utf-8', "PYTHONIOENCODING should be set to utf-8"
            assert env['PYTHONUTF8'] == '1', "PYTHONUTF8 should be set to 1"
            assert env['LANG'] == 'en_US.UTF-8', "LANG should be set to en_US.UTF-8"
            assert env['LC_ALL'] == 'en_US.UTF-8', "LC_ALL should be set to en_US.UTF-8"
            assert env['LC_CTYPE'] == 'en_US.UTF-8', "LC_CTYPE should be set to en_US.UTF-8"
            assert env['PYTHONLEGACYWINDOWSSTDIO'] == '0', "PYTHONLEGACYWINDOWSSTDIO should be set to 0"
            
            # Check encoding parameters
            assert call_kwargs['encoding'] == 'utf-8', "Encoding should be utf-8"
            assert call_kwargs['errors'] == 'replace', "Error handling should be 'replace'"
            assert call_kwargs['text'] is True, "Text parameter should be True"

    @pytest.mark.skip(reason="Test expects subprocess calls but implementation uses yt-dlp Python API")
    def test_metadata_service_encoding_environment(self):
        """Test that YouTubeMetadataService sets proper encoding environment variables."""
        service = YouTubeMetadataService()
        
        # Mock subprocess.run to capture environment
        with patch('services.youtube.metadata_service.subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Test Title\n120"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result
            
            # Call the metadata service
            service._get_basic_video_info("https://youtube.com/watch?v=test")
            
            # Verify subprocess was called with proper environment
            mock_subprocess.assert_called()
            call_kwargs = mock_subprocess.call_args[1]
            
            assert 'env' in call_kwargs, "subprocess.run should be called with env parameter"
            env = call_kwargs['env']
            
            # Check critical encoding environment variables
            assert env['PYTHONIOENCODING'] == 'utf-8', "PYTHONIOENCODING should be set to utf-8"
            assert env['PYTHONUTF8'] == '1', "PYTHONUTF8 should be set to 1"
            assert env['LANG'] == 'en_US.UTF-8', "LANG should be set to en_US.UTF-8"
            assert env['LC_ALL'] == 'en_US.UTF-8', "LC_ALL should be set to en_US.UTF-8"
            assert env['LC_CTYPE'] == 'en_US.UTF-8', "LC_CTYPE should be set to en_US.UTF-8"
            assert env['PYTHONLEGACYWINDOWSSTDIO'] == '0', "PYTHONLEGACYWINDOWSSTDIO should be set to 0"

    @pytest.mark.skip(reason="Test expects subprocess calls but ServiceController uses yt-dlp Python API")
    def test_unicode_decode_error_fallback(self):
        """Test that UnicodeDecodeError is handled with fallback encoding."""
        controller = ServiceController(Mock(), Mock())
        
        # Mock subprocess.run to raise UnicodeDecodeError first, then succeed
        with patch('core.service_controller.subprocess.run') as mock_subprocess:
            # First call raises UnicodeDecodeError
            # Second call (fallback) succeeds
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Success with fallback"
            mock_result.stderr = ""
            
            mock_subprocess.side_effect = [
                UnicodeDecodeError('utf-8', b'problematic bytes', 0, 1, 'invalid start byte'),
                mock_result
            ]
            
            # Create a mock download
            download = Mock()
            download.name = "Test Video"
            download.url = "https://youtube.com/watch?v=test"
            download.quality = "720p"
            download.output_path = "~/Downloads"
            download.audio_only = False
            download.download_playlist = False
            download.download_subtitles = False
            download.selected_subtitles = []
            download.download_thumbnail = True
            download.embed_metadata = True
            download.cookie_path = None
            download.selected_browser = None
            
            completion_callback = Mock()
            
            # This should NOT raise an exception and should use fallback
            controller._download_worker(download, "~/Downloads", None, completion_callback)
            
            # Verify subprocess was called twice (original + fallback)
            assert mock_subprocess.call_count == 2, "Should call subprocess twice (original + fallback)"
            
            # Check that fallback used latin-1 encoding
            fallback_call = mock_subprocess.call_args_list[1]
            fallback_kwargs = fallback_call[1]
            assert fallback_kwargs['encoding'] == 'latin-1', "Fallback should use latin-1 encoding"
            
            # Verify success callback was called
            completion_callback.assert_called_once()
            args = completion_callback.call_args[0]
            assert args[0] is True, "Download should succeed with fallback"

    @pytest.mark.skip(reason="Test expects subprocess calls but ServiceController uses yt-dlp Python API")
    def test_yt_dlp_command_encoding_options(self):
        """Test that yt-dlp commands include encoding-friendly options."""
        controller = ServiceController(Mock(), Mock())
        
        # Mock subprocess.run to capture command
        with patch('core.service_controller.subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Success"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result
            
            # Create a mock download
            download = Mock()
            download.name = "Test Video"
            download.url = "https://youtube.com/watch?v=test"
            download.quality = "720p"
            download.output_path = "~/Downloads"
            download.audio_only = False
            download.download_playlist = False
            download.download_subtitles = False
            download.selected_subtitles = []
            download.download_thumbnail = True
            download.embed_metadata = True
            download.cookie_path = None
            download.selected_browser = None
            
            # Call the download worker
            controller._download_worker(download, "~/Downloads", None, None)
            
            # Verify subprocess was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args[0]
            cmd = call_args[0]
            
            # Check that encoding-friendly options are included
            assert '--no-check-certificate' in cmd, "Should include --no-check-certificate"
            assert '--ignore-errors' in cmd, "Should include --ignore-errors"
            assert '--no-warnings' in cmd, "Should include --no-warnings"
            assert '--extractor-args' in cmd, "Should include extractor args"

    def test_safe_decode_bytes_method(self):
        """Test the _safe_decode_bytes method with various problematic byte sequences."""
        controller = ServiceController(Mock(), Mock())
        
        # Test cases with problematic byte sequences
        test_cases = [
            # Valid UTF-8
            (b'Normal text', 'Normal text'),
            # UTF-8 with special characters
            ('Text with special chars: \xa7 \xb0 \xb3'.encode('utf-8'), 'Text with special chars: § ° ³'),
            # Invalid UTF-8 that should fallback to latin-1
            (b'Text with invalid UTF-8: \xdb\xef', 'Text with invalid UTF-8: Ûï'),
            # The specific 0xb0 byte that was causing the issue
            (b'Some text with problematic byte: \xb0 and more', 'Some text with problematic byte: ° and more'),
            # More problematic bytes
            (b'Error: \xb0\xb1\xb2\xb3\xb4\xb5', 'Error: °±²³´µ'),
            # Empty bytes
            (b'', ''),
            # Mixed content
            (b'Some text \xa7 with \xdb problematic \xb3 bytes', 'Some text § with Û problematic ³ bytes')
        ]
        
        for i, (test_bytes, expected) in enumerate(test_cases):
            result = controller._safe_decode_bytes(test_bytes)
            assert result == expected, f"Test {i+1} failed: expected {expected!r}, got {result!r}"

    @pytest.mark.skip(reason="Test expects subprocess calls but ServiceController uses yt-dlp Python API")
    def test_original_error_scenario_handling(self):
        """Test the exact scenario that caused the original 0xb0 error."""
        controller = ServiceController(Mock(), Mock())
        
        # Simulate the exact error scenario from the original issue
        with patch('core.service_controller.subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 1
            # This is the exact error message from the original issue
            mock_result.stdout = "Some normal output"
            mock_result.stderr = "ERROR: 'utf-8' codec can't decode byte 0xb0 in position 31: invalid start byte"
            mock_subprocess.return_value = mock_result
            
            download = Mock()
            download.name = "5 Minute English | 12 English Lessons for the Holidays"
            download.url = "https://youtube.com/watch?v=test"
            download.quality = "720p"
            download.output_path = "~/Downloads"
            download.audio_only = False
            download.download_playlist = False
            download.download_subtitles = False
            download.selected_subtitles = []
            download.download_thumbnail = True
            download.embed_metadata = True
            download.cookie_path = None
            download.selected_browser = None
            
            completion_callback = Mock()
            
            # This should NOT raise an exception
            controller._download_worker(download, "~/Downloads", None, completion_callback)
            
            # Verify the error was handled gracefully
            completion_callback.assert_called_once()
            args = completion_callback.call_args[0]
            assert args[0] is False, "Download should fail gracefully"
            assert "0xb0" in args[1], "Error message should contain the problematic byte reference"
            
            # Verify subprocess was called with proper encoding parameters
            mock_subprocess.assert_called_once()
            call_kwargs = mock_subprocess.call_args[1]
            assert call_kwargs['encoding'] == 'utf-8', "Should use UTF-8 encoding"
            assert call_kwargs['errors'] == 'replace', "Should use 'replace' error handling"

    @pytest.mark.skip(reason="Test expects subprocess calls but ServiceController uses yt-dlp Python API")
    def test_utf8_error_fallback_to_ios_client(self):
        """Test that UTF-8 errors trigger fallback to iOS client."""
        controller = ServiceController(Mock(), Mock())
        
        # Mock subprocess.run to simulate UTF-8 error, then iOS client success
        with patch('core.service_controller.subprocess.run') as mock_subprocess:
            # First call fails with UTF-8 error
            mock_result_fail = Mock()
            mock_result_fail.returncode = 1
            mock_result_fail.stdout = "Some output"
            mock_result_fail.stderr = "ERROR: 'utf-8' codec can't decode byte 0xb0 in position 31: invalid start byte"
            
            # Second call (iOS client) succeeds
            mock_result_success = Mock()
            mock_result_success.returncode = 0
            mock_result_success.stdout = "Success with iOS client"
            mock_result_success.stderr = ""
            
            mock_subprocess.side_effect = [mock_result_fail, mock_result_success]
            
            download = Mock()
            download.name = "Test Video"
            download.url = "https://youtube.com/watch?v=test"
            download.quality = "720p"
            download.output_path = "~/Downloads"
            download.audio_only = False
            download.download_playlist = False
            download.download_subtitles = False
            download.selected_subtitles = []
            download.download_thumbnail = True
            download.embed_metadata = True
            download.cookie_path = None
            download.selected_browser = None
            
            completion_callback = Mock()
            
            # This should try iOS client and succeed
            controller._download_worker(download, "~/Downloads", None, completion_callback)
            
            # Verify subprocess was called twice (original + iOS client)
            assert mock_subprocess.call_count == 2, "Should call subprocess twice (original + iOS client)"
            
            # Check that iOS client was used
            ios_call = mock_subprocess.call_args_list[1]
            ios_cmd = ios_call[0][0]
            assert 'youtube:player_client=ios' in ios_cmd, "Should use iOS client in fallback"
            
            # Verify success callback was called
            completion_callback.assert_called_once()
            args = completion_callback.call_args[0]
            assert args[0] is True, "Download should succeed with iOS client"

    @pytest.mark.parametrize("problematic_bytes,expected", [
        (b'Normal text', 'Normal text'),
        ('Text with special chars: \xa7 \xb0 \xb3'.encode('utf-8'), 'Text with special chars: § ° ³'),
        (b'Text with invalid UTF-8: \xdb\xef', 'Text with invalid UTF-8: Ûï'),
        (b'Some text with problematic byte: \xb0 and more', 'Some text with problematic byte: ° and more'),
        (b'Error: \xb0\xb1\xb2\xb3\xb4\xb5', 'Error: °±²³´µ'),
        (b'', ''),
        (b'Some text \xa7 with \xdb problematic \xb3 bytes', 'Some text § with Û problematic ³ bytes')
    ])
    def test_safe_decode_bytes_parametrized(self, problematic_bytes, expected):
        """Parametrized test for _safe_decode_bytes method."""
        controller = ServiceController(Mock(), Mock())
        result = controller._safe_decode_bytes(problematic_bytes)
        assert result == expected, f"Expected {expected!r}, got {result!r}"

    @pytest.mark.skip(reason="Test expects subprocess calls but implementation uses yt-dlp Python API")
    def test_metadata_service_subprocess_encoding_parameters(self):
        """Test that YouTubeMetadataService subprocess calls use proper encoding."""
        service = YouTubeMetadataService()
        
        # Test all subprocess calls in the metadata service
        with patch('services.youtube.metadata_service.subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "Title\n120"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result
            
            # This should call subprocess.run with encoding parameters
            service._get_basic_video_info("https://youtube.com/watch?v=test")
            
            # Verify the call
            mock_subprocess.assert_called()
            call_kwargs = mock_subprocess.call_args[1]
            
            assert 'encoding' in call_kwargs, "subprocess.run should be called with encoding parameter"
            assert call_kwargs['encoding'] == 'utf-8', f"Expected UTF-8 encoding, got {call_kwargs.get('encoding')}"
            assert 'errors' in call_kwargs, "subprocess.run should be called with errors parameter"
            assert call_kwargs['errors'] == 'replace', f"Expected 'replace' error handling, got {call_kwargs.get('errors')}"
            assert 'text' in call_kwargs, "subprocess.run should be called with text parameter"
            assert call_kwargs['text'] is True, f"Expected text=True, got {call_kwargs.get('text')}"
