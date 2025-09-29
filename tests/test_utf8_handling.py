"""Test UTF-8 handling in subprocess calls."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_utf8_decoding_fallback():
    """Test the UTF-8 decoding fallback mechanism."""
    # Import the service controller
    from core.service_controller import ServiceController
    from unittest.mock import Mock

    # Create a service controller instance
    controller = ServiceController(Mock(), Mock())

    # Test cases with problematic byte sequences
    test_cases = [
        # Valid UTF-8
        (b'Normal text', 'Normal text'),
        # UTF-8 with special characters
        ('Text with special chars: \xa7 \xb3 \xb4'.encode('utf-8'), 'Text with special chars: § ³ ´'),
        # Invalid UTF-8 that should fallback to latin-1
        (b'Text with invalid UTF-8: \xdb\xef', 'Text with invalid UTF-8: Ûï'),
        # More problematic bytes
        (b'\x80\x81\x82\x83', '\x80\x81\x82\x83'),
        # Empty bytes
        (b'', ''),
        # Mixed content
        (b'Some text \xa7 with \xdb problematic \xb3 bytes', 'Some text § with Û problematic ³ bytes')
    ]

    for i, (test_bytes, expected) in enumerate(test_cases):
        result = controller._safe_decode_bytes(test_bytes)
        assert result == expected, f"Test {i+1} failed: expected {expected!r}, got {result!r}"

def test_problematic_ytdlp_output():
    """Test decoding of problematic yt-dlp output."""
    from core.service_controller import ServiceController
    from unittest.mock import Mock

    controller = ServiceController(Mock(), Mock())

    # Simulate actual yt-dlp error output that caused issues
    problematic_outputs = [
        # Output with problematic bytes
        (b'ERROR: \xa7 Invalid character in output \xb3',
         'ERROR: § Invalid character in output ³'),
        # Mixed encoding issues
        (b'ERROR: Video unavailable \xdb with special chars',
         'ERROR: Video unavailable Û with special chars'),
        # Normal output
        (b'[download] 100% of 10.00MiB',
         '[download] 100% of 10.00MiB'),
        # Mixed content
        (b'[info] Video title: \xa7 Special \xb3 Characters \xb4',
         '[info] Video title: § Special ³ Characters ´')
    ]

    for i, (test_bytes, expected) in enumerate(problematic_outputs):
        result = controller._safe_decode_bytes(test_bytes)
        assert result == expected, f"Output test {i+1} failed: expected {expected!r}, got {result!r}"

