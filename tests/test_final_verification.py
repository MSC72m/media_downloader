"""Final verification test to confirm the issue and provide solution."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_command_line_vs_api():
    """Test command line vs Python API behavior."""
    print("🔍 Testing Command Line vs Python API")
    print("=" * 50)

    try:
        import yt_dlp
        import subprocess

        url = 'https://www.youtube.com/watch?v=16rzTkkW7_E'

        # Test 1: Command line
        print("\n1. Testing command line...")
        try:
            result = subprocess.run([
                'source .venv/bin/activate && yt-dlp',
                '--cookies-from-browser', 'chrome',
                '--quiet', '--skip-download', '--no-warnings',
                '--print', 'title',
                url
            ], shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"   ✅ Command line success: {result.stdout.strip()}")
            else:
                print(f"   ❌ Command line failed: {result.stderr.strip()}")
        except Exception as e:
            print(f"   ❌ Command line error: {e}")

        # Test 2: Python API with same options
        print("\n2. Testing Python API...")
        try:
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

            print(f"   Options: {ydl_opts}")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                print(f"   ✅ Python API success: {info.get('title', 'Unknown')}")

        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ Python API failed: {error_msg}")

            if "Sign in to confirm you're not a bot" in error_msg:
                print("   🤔 This suggests the Python API has different cookie handling")
                print("   than the command line version")

    except ImportError:
        print("❌ yt-dlp not available")

def test_cookie_extraction_verification():
    """Test if cookies are actually being extracted."""
    print("\n🍪 Testing Cookie Extraction")
    print("=" * 50)

    try:
        import yt_dlp

        # Create a custom YoutubeDL to see cookie extraction
        class VerboseYoutubeDL(yt_dlp.YoutubeDL):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                print("   📝 VerboseYoutubeDL initialized")

            def extract_info(self, *args, **kwargs):
                print("   🔍 Starting extraction...")
                return super().extract_info(*args, **kwargs)

        ydl_opts = {
            'quiet': False,  # Enable verbose output
            'no_warnings': False,
            'skip_download': True,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'noplaylist': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': 0,
            'cookies_from_browser': 'chrome'
        }

        print("\n3. Testing with verbose output...")
        try:
            with VerboseYoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info('https://www.youtube.com/watch?v=16rzTkkW7_E', download=False)
                print(f"   ✅ Verbose success: {info.get('title', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ Verbose failed: {e}")

    except ImportError:
        print("❌ yt-dlp not available")

def test_alternative_approach():
    """Test alternative cookie handling approaches."""
    print("\n🔄 Testing Alternative Approaches")
    print("=" * 50)

    try:
        import yt_dlp
        url = 'https://www.youtube.com/watch?v=16rzTkkW7_E'

        # Test 1: Try different Chrome profile specifications
        chrome_profiles = [
            'chrome',
            'chrome:Default',
            'chrome:Profile 1'
        ]

        for profile in chrome_profiles:
            print(f"\n4. Testing Chrome profile: {profile}")
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'cookies_from_browser': profile
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    print(f"   ✅ Success with {profile}: {info.get('title', 'Unknown')}")
                    break

            except Exception as e:
                print(f"   ❌ Failed with {profile}: {str(e)[:100]}...")

        # Test 2: Try manual cookie file approach
        print("\n5. Testing if we can create a working cookie file...")

        # Try to extract Chrome cookies to a file manually
        try:
            import tempfile
            import sqlite3

            # This would be a more complex approach
            print("   📝 Manual cookie extraction would require:")
            print("      - Finding Chrome cookie database")
            print("      - Decrypting Chrome cookies (complex on macOS)")
            print("      - Converting to Netscape format")
            print("   💡 This is why --cookies-from-browser is preferred")

        except Exception as e:
            print(f"   ❌ Manual approach not feasible: {e}")

    except ImportError:
        print("❌ yt-dlp not available")

if __name__ == "__main__":
    print("🧪 Final Verification Test")
    print("=" * 60)

    test_command_line_vs_api()
    test_cookie_extraction_verification()
    test_alternative_approach()

    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("The issue appears to be that Python API cookie handling")
    print("is different from command line cookie handling in yt-dlp.")
    print("This might be a known issue with yt-dlp's Python API.")
    print("\n💡 Potential solutions:")
    print("1. Use command line yt-dlp instead of Python API")
    print("2. Try different Chrome profile specifications")
    print("3. Use manual cookie files (complex on macOS)")
    print("4. Check yt-dlp version and known issues")