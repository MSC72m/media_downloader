#!/usr/bin/env python3
"""Download Chromium browser for Playwright.

This script downloads the Chromium browser binary that Playwright uses
and places it in the bin/chromium directory for bundling.

Usage:
    python scripts/download_chromium.py
    BUNDLE_CHROMIUM=1 python scripts/build_windows.bat installer

The Chromium browser will be placed at:
    bin/chromium/
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BIN_DIR = Path("bin")
CHROMIUM_DIR = BIN_DIR / "chromium"


def download_chromium() -> bool:
    """Use Playwright to download Chromium to a specific location."""
    print("=" * 60)
    print("Chromium Browser Downloader for Playwright")
    print("=" * 60)
    print()

    # Check if already exists
    if CHROMIUM_DIR.exists():
        print(f"Chromium directory exists: {CHROMIUM_DIR}")
        # Verify it's actually there
        try:
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if "already installed" in (result.stdout + result.stderr).lower():
                print("Chromium is already installed")
                return True
        except Exception:
            pass

    print("Downloading Chromium browser...")
    print("This may take 2-5 minutes depending on your connection.")
    print()

    # Create bin directory
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Use playwright install with custom download path
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(CHROMIUM_DIR.absolute())

        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            env=env,
            capture_output=False,  # Show progress
            text=True,
            timeout=600,
            check=False,  # 10 minute timeout
        )

        if result.returncode == 0:
            print()
            print("Chromium downloaded successfully!")
            print(f"  Location: {CHROMIUM_DIR}")

            # Get the size
            total_size = sum(f.stat().st_size for f in CHROMIUM_DIR.rglob("*") if f.is_file())
            print(f"  Size: {total_size // 1024 // 1024} MB")
            return True
        print()
        print("Chromium download failed")
        return False

    except subprocess.TimeoutExpired:
        print()
        print("Download timed out after 10 minutes")
        return False

    except Exception as e:
        print()
        print(f"Error: {e}")
        return False


def main() -> int:
    """Main entry point."""
    if download_chromium():
        print()
        print("You can now build the installer with Chromium bundled:")
        print("  BUNDLE_CHROMIUM=1 python scripts/build_windows.bat installer")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
