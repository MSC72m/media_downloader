#!/usr/bin/env python3
"""Download ffmpeg for Windows.

This script downloads a static ffmpeg build for Windows and extracts it
to the bin/ directory for bundling with the application.

Usage:
    python scripts/download_ffmpeg.py

The ffmpeg binary will be placed at:
    bin/ffmpeg.exe
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# Configuration
FFMPEG_VERSION = "6.1.1"
DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
BIN_DIR = Path("bin")


def download_file(url: str, dest: Path, desc: str = "Downloading") -> None:
    """Download a file with progress reporting."""
    print(f"{desc}...")
    print(f"  URL: {url}")
    print(f"  Destination: {dest}")

    def report_hook(block_num: int, block_size: int, total_size: int) -> None:
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(downloaded / total_size * 100, 100)
            print(
                f"\r  Progress: {percent:.1f}% ({downloaded // 1024 // 1024} MB / {total_size // 1024 // 1024} MB)",
                end="",
                flush=True,
            )

    urllib.request.urlretrieve(url, dest, reporthook=report_hook)  # noqa: S310
    print()  # Newline after progress


def extract_ffmpeg(zip_path: Path, dest_dir: Path) -> None:
    """Extract ffmpeg.exe from the zip file."""
    print(f"Extracting {zip_path}...")

    with zipfile.ZipFile(zip_path, "r") as zf:
        # Find ffmpeg.exe in the zip
        ffmpeg_exe = None
        for name in zf.namelist():
            if name.endswith(("bin/ffmpeg.exe", "bin\\ffmpeg.exe")):
                ffmpeg_exe = name
                break

        if not ffmpeg_exe:
            raise RuntimeError("ffmpeg.exe not found in the downloaded archive")

        print(f"  Found: {ffmpeg_exe}")

        # Extract just the ffmpeg.exe
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "ffmpeg.exe"

        with zf.open(ffmpeg_exe) as src, open(dest_path, "wb") as dst:
            shutil.copyfileobj(src, dst)

        print(f"  Extracted to: {dest_path}")


def verify_ffmpeg(bin_dir: Path) -> bool:
    """Check if ffmpeg is available and working."""
    ffmpeg_path = bin_dir / "ffmpeg.exe"
    if not ffmpeg_path.exists():
        return False

    try:
        import subprocess

        result = subprocess.run(
            [str(ffmpeg_path), "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("FFmpeg Downloader for Windows")
    print("=" * 60)
    print()

    # Check if already downloaded
    if verify_ffmpeg(BIN_DIR):
        print(f"✓ ffmpeg already exists and is working: {BIN_DIR / 'ffmpeg.exe'}")
        return 0

    # Create bin directory
    BIN_DIR.mkdir(parents=True, exist_ok=True)

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        download_file(DOWNLOAD_URL, tmp_path, "Downloading ffmpeg")
        extract_ffmpeg(tmp_path, BIN_DIR)

        if verify_ffmpeg(BIN_DIR):
            print()
            print("✓ ffmpeg downloaded and verified successfully!")
            print(f"  Location: {BIN_DIR / 'ffmpeg.exe'}")
            return 0
        print()
        print("✗ ffmpeg verification failed")
        return 1

    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1

    finally:
        # Cleanup
        if tmp_path.exists():
            tmp_path.unlink()


if __name__ == "__main__":
    sys.exit(main())
