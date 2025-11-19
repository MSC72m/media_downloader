#!/usr/bin/env python3
"""Post-install script to set up Playwright Chromium browser.

This script is run after installing dependencies to ensure Playwright's
Chromium browser is installed and ready to use.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Install Playwright Chromium browser."""
    print("\n" + "=" * 70)
    print("  Setting up Playwright Chromium Browser")
    print("=" * 70)
    print("\nThis will download and install Chromium (~150MB)...")
    print("This only needs to be done once.\n")

    try:
        # Run playwright install chromium
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        print("\n" + "=" * 70)
        print("  ✅ Playwright Chromium installed successfully!")
        print("=" * 70)
        print("\nYou can now run the Media Downloader:")
        print("  uv run -m src.main")
        print()

        return 0

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 70)
        print("  ❌ Failed to install Playwright Chromium")
        print("=" * 70)
        print(f"\nError: {e}")
        if e.stdout:
            print("\nStdout:", e.stdout)
        if e.stderr:
            print("\nStderr:", e.stderr)
        print("\nPlease try running manually:")
        print("  playwright install chromium")
        print()
        return 1

    except Exception as e:
        print("\n" + "=" * 70)
        print("  ❌ Unexpected error")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nPlease try running manually:")
        print("  playwright install chromium")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
