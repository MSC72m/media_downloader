"""Centralized ffmpeg detection, path resolution, and auto-download.

Single source of truth for all ffmpeg lookups across the application.
Search order:
  1. Next to the running exe  ({app}/bin/ffmpeg.exe or bin/ffmpeg)
  2. Inside PyInstaller _internal/  (portable bundle)
  3. System PATH
  4. Auto-download if none found (first-run — Windows + Linux)
"""

from __future__ import annotations

import contextlib
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from tkinter import Tk

logger = get_logger(__name__)

_FFMPEG_WIN_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
_FFMPEG_LINUX_URLS = {
    "x86_64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    "aarch64": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz",
}
_FFMPEG_LINUX_FALLBACK = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-linux64-gpl.tar.xz"
)

_cache: dict[str, str | None] = {}


def _ffmpeg_name() -> str:
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"


def _get_bin_dir() -> Path:
    """Return the directory where ffmpeg should be stored."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        return exe_dir / "bin"
    return Path(__file__).resolve().parent.parent.parent / "bin"


def _discover_ffmpeg() -> str | None:
    """Locate ffmpeg by checking known locations, then system PATH."""
    name = _ffmpeg_name()
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]

        candidates = [
            meipass / "bin" / name,
            exe_dir / "bin" / name,
            exe_dir / "_internal" / "bin" / name,
        ]

        for candidate in candidates:
            if candidate.exists():
                return str(candidate)

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    return None


def get_ffmpeg_path() -> str | None:
    """Return the full path to ffmpeg, or None if not found. Cached."""
    if "path" not in _cache:
        _cache["path"] = _discover_ffmpeg()
        if _cache["path"]:
            logger.info("[FFMPEG] Found at %s", _cache["path"])
        else:
            logger.warning("[FFMPEG] Not found on system or in app bundle")
    return _cache["path"]


def is_ffmpeg_available() -> bool:
    """Return True if ffmpeg can be found. Cached."""
    return get_ffmpeg_path() is not None


def get_ffmpeg_dir() -> str | None:
    """Return the directory containing ffmpeg (for yt-dlp ffmpeg_location)."""
    path = get_ffmpeg_path()
    return str(Path(path).parent) if path else None


def _download_extract_win(
    dest: Path,
    progress_callback: object = None,
) -> str | None:
    """Download and extract ffmpeg.exe for Windows."""
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    tmp_zip = Path(tmp_path)

    try:

        def _report(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and progress_callback and hasattr(progress_callback, "configure"):
                downloaded = block_num * block_size
                pct = min(downloaded * 100 // total_size, 100)
                with contextlib.suppress(Exception):
                    cast(Any, progress_callback).configure(text=f"Downloading ffmpeg... {pct}%")

        urllib.request.urlretrieve(_FFMPEG_WIN_URL, str(tmp_zip), _report)

        logger.info("[FFMPEG] Extracting ffmpeg.exe...")
        with zipfile.ZipFile(str(tmp_zip), "r") as zf:
            for name in zf.namelist():
                if name.endswith(("bin/ffmpeg.exe", "bin\\ffmpeg.exe")):
                    with zf.open(name) as src, open(dest, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    break
            else:
                logger.error("[FFMPEG] ffmpeg.exe not found in downloaded archive")
                return None
    except Exception as e:
        logger.error("[FFMPEG] Download failed: %s", e)
        return None
    finally:
        tmp_zip.unlink(missing_ok=True)
        os.close(tmp_fd)

    if dest.exists() and dest.stat().st_size > 0:
        return str(dest)
    return None


def _extract_ffmpeg_from_tar(archive: Path, dest: Path) -> bool:
    """Extract ffmpeg binary from a tar.xz archive. Returns True on success."""
    extract_dir = Path(tempfile.mkdtemp())
    try:
        subprocess.run(
            ["tar", "-xJf", str(archive), "-C", str(extract_dir)],
            check=True,
            capture_output=True,
        )
        for root, _dirs, files in os.walk(extract_dir):
            for name in files:
                if name == "ffmpeg":
                    shutil.copy2(Path(root) / name, dest)
                    dest.chmod(0o755)
                    return True
        return False
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


def _download_extract_linux(dest: Path) -> str | None:
    """Download and extract static ffmpeg binary for Linux."""
    arch = platform.machine()
    url = _FFMPEG_LINUX_URLS.get(arch, _FFMPEG_LINUX_FALLBACK)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".tar.xz")
    tmp_file = Path(tmp_path)
    os.close(tmp_fd)

    try:
        logger.info("[FFMPEG] Downloading from %s", url)
        urllib.request.urlretrieve(url, str(tmp_file))
        if _extract_ffmpeg_from_tar(tmp_file, dest):
            return str(dest)
        logger.error("[FFMPEG] ffmpeg binary not found in downloaded archive")
    except Exception as e:
        logger.error("[FFMPEG] Download/extract failed: %s", e)
        if url == _FFMPEG_LINUX_FALLBACK:
            return None
        logger.info("[FFMPEG] Trying fallback URL...")
        try:
            urllib.request.urlretrieve(_FFMPEG_LINUX_FALLBACK, str(tmp_file))
            if _extract_ffmpeg_from_tar(tmp_file, dest):
                return str(dest)
        except Exception as e2:
            logger.error("[FFMPEG] Fallback download also failed: %s", e2)
    finally:
        tmp_file.unlink(missing_ok=True)

    return str(dest) if (dest.exists() and dest.stat().st_size > 0) else None


def download_ffmpeg(progress_callback: object = None) -> str | None:
    """Download ffmpeg and return its path, or None on failure.

    Platform-aware: downloads ffmpeg.exe (Windows) or static ffmpeg (Linux).
    """
    bin_dir = _get_bin_dir()
    dest = bin_dir / _ffmpeg_name()

    if dest.exists():
        _cache["path"] = str(dest)
        return str(dest)

    bin_dir.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        result = _download_extract_win(dest, progress_callback)
    elif sys.platform == "linux":
        result = _download_extract_linux(dest)
    else:
        logger.warning("[FFMPEG] Auto-download not supported on %s", sys.platform)
        return None

    if result:
        _cache["path"] = result
        logger.info("[FFMPEG] Downloaded successfully to %s", dest)
    return result


def ensure_ffmpeg_available(root_window: Tk | None = None) -> None:
    """Ensure ffmpeg is available, downloading in background if needed.

    On Windows, auto-downloads ffmpeg.exe in a background thread. On
    macOS/Linux the automatic download (a Windows build) does not apply, so
    surface a clear, actionable message instead of failing silently later in
    the SoundCloud/audio-extraction path.
    """
    if is_ffmpeg_available():
        return

    label: Any = None
    if root_window is not None:
        status_bar = getattr(root_window, "status_bar", None)
        label = getattr(status_bar, "status_label", None)

    if sys.platform != "win32":
        install_hint = (
            "brew install ffmpeg" if sys.platform == "darwin" else "sudo apt install ffmpeg"
        )
        msg = f"ffmpeg not found — audio downloads need it. Install with: {install_hint}"
        logger.warning("[FFMPEG] %s", msg)
        if label is not None and root_window is not None:
            with contextlib.suppress(Exception):
                root_window.after(0, lambda: label.configure(text=msg))  # type: ignore[union-attr]
        return

    import threading

    def _bg_download() -> None:
        result = download_ffmpeg(progress_callback=label)
        if result:
            logger.info("[FFMPEG] Background download complete")
            if label is not None and root_window is not None:
                with contextlib.suppress(Exception):
                    root_window.after(
                        0,
                        lambda: label.configure(text="ffmpeg ready"),  # type: ignore[union-attr]
                    )
        else:
            logger.warning("[FFMPEG] Background download failed - video merging may not work")

    threading.Thread(target=_bg_download, daemon=True).start()
