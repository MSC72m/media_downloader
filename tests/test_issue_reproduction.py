"""Test to reproduce the exact cookie authentication issue."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_exact_issue_reproduction():
    """Test the exact scenario that's failing."""
    print("🔍 Reproducing the exact cookie authentication issue...")
    print("=" * 60)

    try:
        import yt_dlp

        # Use the exact same URL and options as in the failing logs
        url = 'https://www.youtube.com/watch?v=SzniwfrUUYs'

        # These are the exact options from our debug logs
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

        print(f"URL: {url}")
        print(f"Options: {ydl_opts}")

        print("\n🧪 Testing with Chrome cookies...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                print(f"✅ Success! Title: {info.get('title', 'Unknown')}")
                print(f"   Duration: {info.get('duration', 'Unknown')} seconds")
                print(f"   Channel: {info.get('channel', 'Unknown')}")
                return True
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed: {error_msg}")

            # Check if it's the same error we're seeing
            if "Sign in to confirm you're not a bot" in error_msg:
                print("🤔 This is the same authentication error we're seeing in the app")
                print("🔍 This suggests that while Chrome cookies are being extracted,")
                print("   they might not contain the necessary authentication for this specific video")
                return False
            elif "nsig extraction failed" in error_msg:
                print("⚠️ This is a signature extraction issue, not a cookie issue")
                print("   This means cookies are working but there's a separate YouTube signature problem")
                return True
            else:
                print(f"❓ Unexpected error: {error_msg}")
                return False

    except ImportError:
        print("❌ yt-dlp not available")
        return False

def test_different_videos():
    """Test with different videos to isolate the issue."""
    print("\n🧪 Testing with different videos...")

    try:
        import yt_dlp

        # Test videos with different restrictions
        test_videos = [
            ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', "Rick Astley - Never Gonna Give You Up"),
            ('https://www.youtube.com/watch?v=jNQXAC9IVRw', "Me at the zoo"),
            ('https://www.youtube.com/watch?v=9bZkp7q19f0', "PSY - GANGNAM STYLE")
        ]

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

        for url, description in test_videos:
            print(f"\n📹 Testing: {description}")
            print(f"   URL: {url}")

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    print(f"   ✅ Success: {info.get('title', 'Unknown')}")
            except Exception as e:
                error_msg = str(e)
                if "Sign in to confirm you're not a bot" in error_msg:
                    print(f"   🔒 Authentication required: {error_msg}")
                elif "nsig extraction failed" in error_msg:
                    print(f"   ⚠️ Signature issue (cookies working): {error_msg}")
                else:
                    print(f"   ❌ Other error: {error_msg}")

    except ImportError:
        print("❌ yt-dlp not available")

def test_browser_comparison():
    """Test different browsers to see if any work better."""
    print("\n🌐 Testing different browsers...")

    try:
        import yt_dlp

        url = 'https://www.youtube.com/watch?v=SzniwfrUUYs'
        browsers = ['chrome', 'firefox', 'safari']

        for browser in browsers:
            print(f"\n🔍 Testing {browser}...")
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': False,
                'writeautomaticsub': False,
                'noplaylist': True,
                'extract_flat': 'discard_in_playlist',
                'playlistend': 0,
                'cookies_from_browser': browser
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    print(f"   ✅ {browser} works: {info.get('title', 'Unknown')}")
            except Exception as e:
                error_msg = str(e)
                if "could not find" in error_msg:
                    print(f"   ❓ {browser} not available: {error_msg}")
                elif "Sign in to confirm you're not a bot" in error_msg:
                    print(f"   🔒 {browser} auth failed: {error_msg}")
                else:
                    print(f"   ❌ {browser} error: {error_msg}")

    except ImportError:
        print("❌ yt-dlp not available")

if __name__ == "__main__":
    print("🧪 YouTube Cookie Authentication Issue Reproduction")
    print("=" * 60)

    success = test_exact_issue_reproduction()
    test_different_videos()
    test_browser_comparison()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Issue appears to be resolved!")
    else:
        print("🔍 Issue reproduced - this is indeed a cookie authentication problem")
        print("💡 The issue might be:")
        print("   1. Chrome cookies don't contain authentication for this specific video")
        print("   2. The video requires additional authentication beyond basic cookies")
        print("   3. There might be browser-specific cookie encryption issues")
        print("\n📝 Try testing with different videos or browsers")