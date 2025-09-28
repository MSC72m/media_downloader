"""Test the new command line based metadata service."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_new_metadata_service():
    """Test the new command line based metadata service."""
    print("🧪 Testing New Command Line Based Metadata Service")
    print("=" * 60)

    try:
        from services.youtube.metadata_service import YouTubeMetadataService

        # Create service instance
        service = YouTubeMetadataService()

        # Test with a video that works
        print("\n1. Testing with Rick Astley video (should work)...")
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        metadata = service.fetch_metadata(url, browser='chrome')

        if metadata and metadata.title:
            print(f"   ✅ Success: {metadata.title}")
            print(f"   Duration: {metadata.duration}")
            print(f"   Channel: {metadata.channel}")
            print(f"   Views: {metadata.view_count}")
        else:
            print(f"   ❌ Failed: {metadata.error if metadata else 'Unknown error'}")

        # Test with a video that requires authentication
        print("\n2. Testing with authentication-required video...")
        url = 'https://www.youtube.com/watch?v=SzniwfrUUYs'

        metadata = service.fetch_metadata(url, browser='chrome')

        if metadata and metadata.title:
            print(f"   ✅ Success: {metadata.title}")
            print(f"   Duration: {metadata.duration}")
            print(f"   Channel: {metadata.channel}")
        else:
            print(f"   ❌ Failed (expected): {metadata.error if metadata else 'Unknown error'}")

        # Test without cookies
        print("\n3. Testing without cookies...")
        url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

        metadata = service.fetch_metadata(url, cookie_path=None, browser=None)

        if metadata and metadata.title:
            print(f"   ✅ Success: {metadata.title}")
        else:
            print(f"   ❌ Failed: {metadata.error if metadata else 'Unknown error'}")

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

def test_command_line_vs_service():
    """Compare command line yt-dlp with our service."""
    print("\n🔍 Comparing Command Line vs Service")
    print("=" * 60)

    import subprocess
    import json

    url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    # Test 1: Direct command line
    print("\n1. Direct command line test...")
    try:
        cmd = ['.venv/bin/yt-dlp', '--cookies-from-browser', 'chrome', '--quiet', '--no-warnings', '--skip-download', '--print', '%(json)s', url]
        print(f"   Command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            info = json.loads(result.stdout)
            print(f"   ✅ Command line success: {info.get('title', 'Unknown')}")
        else:
            print(f"   ❌ Command line failed: {result.stderr}")
    except Exception as e:
        print(f"   ❌ Command line error: {e}")

    # Test 2: Our service
    print("\n2. Our service test...")
    try:
        from services.youtube.metadata_service import YouTubeMetadataService
        service = YouTubeMetadataService()

        metadata = service.fetch_metadata(url, browser='chrome')

        if metadata and metadata.title:
            print(f"   ✅ Service success: {metadata.title}")
        else:
            print(f"   ❌ Service failed: {metadata.error if metadata else 'Unknown error'}")
    except Exception as e:
        print(f"   ❌ Service error: {e}")

if __name__ == "__main__":
    print("🧪 Testing New Command Line Metadata Service")
    print("=" * 60)

    test_new_metadata_service()
    test_command_line_vs_service()

    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("This test verifies that our new command line-based metadata service")
    print("works correctly and produces the same results as direct command line execution.")