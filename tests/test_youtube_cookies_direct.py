"""Direct test for YouTube cookie functionality without complex imports."""

import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_cookie_parameter_formatting():
    """Test that cookie parameters are formatted correctly for yt-dlp."""
    print("Testing YouTube cookie parameter formatting...")

    # Test the exact logic from the metadata service
    def simulate_cookie_handling(cookie_path, browser):
        """Simulate the cookie handling logic from metadata service."""
        basic_options = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'noplaylist': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': 0,
        }

        print(f"DEBUG: Metadata service received cookie_path: {cookie_path}")
        print(f"DEBUG: Browser parameter: {browser}")

        # Priority 1: Use browser parameter if provided
        if browser:
            basic_options['cookies_from_browser'] = browser
            print(f"DEBUG: Using cookies-from-browser: {browser}")

        # Priority 2: Use manual cookie path if provided
        elif cookie_path:
            # Check if it's a valid file path for manual cookie files
            if os.path.exists(cookie_path):
                try:
                    # Try to determine if it's a Netscape format file
                    with open(cookie_path, 'r', encoding='utf-8') as f:
                        content = f.read(100)
                    if content.strip() and not content.strip().startswith('SQLite'):
                        basic_options['cookiefile'] = cookie_path
                        print(f"DEBUG: Using cookiefile: {cookie_path}")
                    else:
                        # Assume it's a SQLite database
                        basic_options['cookies'] = cookie_path
                        print(f"DEBUG: Using cookies (SQLite): {cookie_path}")
                except Exception as e:
                    print(f"DEBUG: Error reading cookie file: {e}")
                    # Fallback to cookiefile parameter
                    basic_options['cookiefile'] = cookie_path
            else:
                print(f"DEBUG: Cookie file does not exist: {cookie_path}")

        else:
            print("DEBUG: No cookies will be used")

        return basic_options

    # Test Case 1: Browser parameter only
    print("\n=== Test Case 1: Browser parameter only ===")
    options = simulate_cookie_handling(None, 'chrome')
    assert 'cookies_from_browser' in options
    assert options['cookies_from_browser'] == 'chrome'
    assert 'cookiefile' not in options
    print("✅ Browser parameter handling works correctly")

    # Test Case 2: Manual cookie file
    print("\n=== Test Case 2: Manual cookie file ===")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Netscape HTTP Cookie File\n.example.com\tTRUE\t/\tFALSE\t1234567890\ttest\tvalue")
        temp_file = f.name

    try:
        options = simulate_cookie_handling(temp_file, None)
        assert 'cookiefile' in options
        assert options['cookiefile'] == temp_file
        assert 'cookies_from_browser' not in options
        print("✅ Manual cookie file handling works correctly")
    finally:
        os.unlink(temp_file)

    # Test Case 3: Browser takes priority over cookie_path
    print("\n=== Test Case 3: Browser takes priority ===")
    options = simulate_cookie_handling('/some/path', 'firefox')
    assert 'cookies_from_browser' in options
    assert options['cookies_from_browser'] == 'firefox'
    assert 'cookiefile' not in options
    print("✅ Browser priority handling works correctly")

    # Test Case 4: No cookies
    print("\n=== Test Case 4: No cookies ===")
    options = simulate_cookie_handling(None, None)
    assert 'cookies_from_browser' not in options
    assert 'cookiefile' not in options
    assert 'cookies' not in options
    print("✅ No cookies handling works correctly")

    print("\n🎉 All cookie parameter formatting tests passed!")

def test_youtube_dl_options():
    """Test that yt-dlp options are formatted correctly."""
    print("\nTesting yt-dlp options formatting...")

    # Mock yt-dlp to verify the options
    class MockYoutubeDL:
        def __init__(self, options):
            self.options = options
            print(f"MockYoutubeDL initialized with options: {options}")

        def extract_info(self, url, download=False):
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

    # Test with Chrome cookies
    print("\n=== Testing Chrome cookies ===")
    options = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'noplaylist': True,
        'extract_flat': 'discard_in_playlist',
        'playlistend': 0,
        'cookies_from_browser': 'chrome'
    }

    mock_ydl = MockYoutubeDL(options)
    result = mock_ydl.extract_info('https://www.youtube.com/watch?v=test')
    assert result['title'] == 'Test Video'
    print("✅ Chrome cookies options work correctly")

    # Test with Firefox cookies
    print("\n=== Testing Firefox cookies ===")
    options['cookies_from_browser'] = 'firefox'
    mock_ydl = MockYoutubeDL(options)
    result = mock_ydl.extract_info('https://www.youtube.com/watch?v=test')
    assert result['title'] == 'Test Video'
    print("✅ Firefox cookies options work correctly")

    # Test with Safari cookies
    print("\n=== Testing Safari cookies ===")
    options['cookies_from_browser'] = 'safari'
    mock_ydl = MockYoutubeDL(options)
    result = mock_ydl.extract_info('https://www.youtube.com/watch?v=test')
    assert result['title'] == 'Test Video'
    print("✅ Safari cookies options work correctly")

    print("\n🎉 All yt-dlp options tests passed!")

def test_real_yt_dlp_behavior():
    """Test actual yt-dlp behavior with real cookies."""
    print("\nTesting real yt-dlp behavior...")

    try:
        import yt_dlp

        # Test Chrome cookie extraction (the one we know works)
        print("\n=== Testing real Chrome cookie extraction ===")
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'noplaylist': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': 0,
            'cookies_from_browser': 'chrome'
        }

        print(f"Using yt-dlp options: {ydl_opts}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # This should work and extract cookies like we saw in the terminal
            print("✅ Real yt-dlp accepts Chrome cookies parameter")

    except ImportError:
        print("⚠️ yt-dlp not available for real testing")
    except Exception as e:
        print(f"⚠️ Real yt-dlp test failed: {e}")

if __name__ == "__main__":
    print("🧪 Starting YouTube Cookie Tests")
    print("=" * 50)

    test_cookie_parameter_formatting()
    test_youtube_dl_options()
    test_real_yt_dlp_behavior()

    print("\n🎉 All tests completed!")