#!/usr/bin/env python3
"""Download a static ffmpeg binary for Linux.

Downloads the latest Linux static build from johnvansickle.com
and extracts the ffmpeg binary to bin/ffmpeg.

Usage:
    python scripts/download_ffmpeg_linux.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BIN_DIR = Path("bin")
ARCH = os.uname().machine
FFMPEG_URL = f"https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-{ARCH}-static.tar.xz"
FALLBACK_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"


def download_file(url: str, dest: Path, desc: str = "Downloading") -> None:
    print(f"{desc}...")
    print(f"  URL: {url}")
    size_mb = 0
    last_pct = -1

    def report(block: int, block_size: int, total: int) -> None:
        nonlocal size_mb, last_pct
        if total > 0:
            downloaded = block * block_size
            pct = min(int(downloaded * 100 / total), 100)
            if pct != last_pct:
                last_pct = pct
                size_mb = total // (1024 * 1024)
                done_mb = downloaded // (1024 * 1024)
                print(f"\r  {pct}% ({done_mb} MB / {size_mb} MB)", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=report)
    print()


def extract_ffmpeg(archive: Path, dest_dir: Path) -> None:
    print(f"Extracting {archive}...")
    if archive.suffix == ".xz" or str(archive).endswith(".tar.xz"):
        extract_dir = Path(tempfile.mkdtemp())
        subprocess.run(
            ["tar", "-xJf", str(archive), "-C", str(extract_dir)],
            check=True,
            capture_output=True,
        )
        try:
            for root, _dirs, files in os.walk(extract_dir):
                for name in files:
                    if name == "ffmpeg":
                        src = Path(root) / name
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        dest = dest_dir / "ffmpeg"
                        shutil.copy2(src, dest)
                        dest.chmod(0o755)
                        print(f"  Extracted to: {dest}")
                        return
            raise RuntimeError("ffmpeg binary not found in tar archive")
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    with zipfile.ZipFile(archive) as zf:
        for name in zf.namelist():
            if name.endswith("ffmpeg"):
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / "ffmpeg"
                with zf.open(name) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                dest.chmod(0o755)
                print(f"  Extracted to: {dest}")
                return
    raise RuntimeError("ffmpeg binary not found in zip archive")


def verify_ffmpeg(bin_dir: Path) -> bool:
    ffmpeg = bin_dir / "ffmpeg"
    if not ffmpeg.exists():
        return False
    try:
        result = subprocess.run(
            [str(ffmpeg), "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def main() -> int:
    print("=" * 60)
    print("FFmpeg Downloader for Linux")
    print("=" * 60)
    print()

    if verify_ffmpeg(BIN_DIR):
        print(f"✓ ffmpeg already exists and is working: {BIN_DIR / 'ffmpeg'}")
        return 0

    BIN_DIR.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_path_str = tempfile.mkstemp(suffix=".tar.xz")
    tmp_path = Path(tmp_path_str)

    try:
        try:
            download_file(FFMPEG_URL, tmp_path, "Downloading ffmpeg (johnvansickle.com)")
        except Exception as e:
            print(f"Primary source failed: {e}")
            print("Trying fallback (GitHub BtbN builds)...")
            download_file(FALLBACK_URL, tmp_path, "Downloading ffmpeg (GitHub fallback)")

        extract_ffmpeg(tmp_path, BIN_DIR)

        if verify_ffmpeg(BIN_DIR):
            print()
            print("✓ ffmpeg downloaded and verified successfully!")
            print(f"  Location: {BIN_DIR / 'ffmpeg'}")
            return 0
        print()
        print("✗ ffmpeg verification failed")
        return 1
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return 1
    finally:
        os.close(tmp_fd)
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
