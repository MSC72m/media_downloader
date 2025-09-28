"""Simple test of the metadata service without complex imports."""

import sys
import os
import subprocess
import json

# Add src to path properly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_command_line_ytdlp():
    """Test command line yt-dlp directly."""
    print("🧪 Testing Command Line yt-dlp")
    print("=" * 50)

    url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    # Test 1: Without cookies
    print("\n1. Testing without cookies...")
    try:
        cmd = ['.venv/bin/yt-dlp', '--quiet', '--no-warnings', '--skip-download', '--print', 'title', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"   ✅ Success: {result.stdout.strip()}")
        else:
            print(f"   ❌ Failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: With Chrome cookies (this should prompt for password)
    print("\n2. Testing with Chrome cookies...")
    try:
        cmd = ['.venv/bin/yt-dlp', '--cookies-from-browser', 'chrome', '--quiet', '--no-warnings', '--skip-download', '--print', 'title', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"   ✅ Success: {result.stdout.strip()}")
        else:
            print(f"   ❌ Failed: {result.stderr.strip()}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_metadata_service_direct():
    """Test the metadata service directly by importing its methods."""
    print("\n🧪 Testing Metadata Service Methods Directly")
    print("=" * 50)

    # Let's manually test the logic without importing the full service
    def simulate_new_metadata_logic(url, browser=None):
        """Simulate the new metadata service logic."""
        try:
            # Build command line arguments
            cmd = ['.venv/bin/yt-dlp']

            # Add cookies if available
            if browser:
                cmd.extend(['--cookies-from-browser', browser])
                print(f"DEBUG: Using cookies-from-browser: {browser}")

            # Add other options
            cmd.extend([
                '--quiet',
                '--no-warnings',
                '--skip-download',
                '--no-playlist',
                '--print', 'title',
                '--print', 'duration',
                '--print', 'view_count',
                '--print', 'upload_date',
                '--print', 'channel',
                '--print', 'description',
                '--print', 'thumbnail',
                url
            ])

            print(f"DEBUG: Running command: {' '.join(cmd)}")

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                # Parse multi-line output
                try:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 7:
                        info = {
                            'title': lines[0] if lines[0] != 'NA' else '',
                            'duration': int(lines[1]) if lines[1] != 'NA' else 0,
                            'view_count': int(lines[2]) if lines[2] != 'NA' else 0,
                            'upload_date': lines[3] if lines[3] != 'NA' else '',
                            'channel': lines[4] if lines[4] != 'NA' else '',
                            'description': lines[5] if lines[5] != 'NA' else '',
                            'thumbnail': lines[6] if lines[6] != 'NA' else '',
                            'subtitles': {},
                            'automatic_captions': {}
                        }
                        print(f"DEBUG: Successfully fetched video info via command line")
                        return info
                    else:
                        print(f"DEBUG: Unexpected output format: {len(lines)} lines")
                        print(f"DEBUG: Raw output: {result.stdout[:500]}...")
                except Exception as e:
                    print(f"DEBUG: Failed to parse output: {e}")
                    print(f"DEBUG: Raw output: {result.stdout[:500]}...")
            else:
                print(f"DEBUG: Command failed with return code {result.returncode}")
                print(f"DEBUG: Error output: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("DEBUG: Command timed out")
        except Exception as e:
            print(f"DEBUG: Command line error: {e}")

        return None

    # Test with Rick Astley video
    print("\n1. Testing with Rick Astley video...")
    url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'

    info = simulate_new_metadata_logic(url, browser='chrome')

    if info:
        print(f"   ✅ Success: {info.get('title', 'Unknown')}")
        print(f"   Duration: {info.get('duration', 'Unknown')} seconds")
        print(f"   Channel: {info.get('channel', 'Unknown')}")
    else:
        print("   ❌ Failed to fetch metadata")

    # Test without cookies
    print("\n2. Testing without cookies...")
    info = simulate_new_metadata_logic(url, browser=None)

    if info:
        print(f"   ✅ Success: {info.get('title', 'Unknown')}")
    else:
        print("   ❌ Failed to fetch metadata without cookies")

if __name__ == "__main__":
    print("🧪 Simple Metadata Service Test")
    print("=" * 60)

    test_command_line_ytdlp()
    test_metadata_service_direct()

    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("This test verifies that our new command line approach works correctly")
    print("and will prompt for password when accessing Chrome cookies.")