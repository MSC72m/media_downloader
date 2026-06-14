"""Centralized ffmpeg detection, path resolution, and auto-download.

Single source of truth for all ffmpeg lookups across the application.
Search order:
  1. Next to the running exe  ({app}/bin/ffmpeg.exe — installed)
  2. Inside PyInstaller _internal/  (portable bundle)
  3. System PATH
  4. Auto-download if none found (first-run)
"""

from __future__ import annotations

import contextlib
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from tkinter import Tk

logger = get_logger(__name__)

_FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

_cache: dict[str, str | None] = {}


def _get_bin_dir() -> Path:
    """Return the directory where ffmpeg should be stored."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        return exe_dir / "bin"
    return Path(__file__).resolve().parent.parent.parent / "bin"


def _discover_ffmpeg() -> str | None:
    """Locate ffmpeg by checking known locations, then system PATH."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]

        candidates = [
            meipass / "bin" / "ffmpeg.exe",  # PyInstaller bundled
            exe_dir / "bin" / "ffmpeg.exe",  # Installed ({app}/bin/)
            exe_dir / "_internal" / "bin" / "ffmpeg.exe",  # Portable layout
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
    """Return the directory containing ffmpeg.exe (for yt-dlp ffmpeg_location)."""
    path = get_ffmpeg_path()
    return str(Path(path).parent) if path else None


def download_ffmpeg(progress_callback: object = None) -> str | None:
    """Download ffmpeg for Windows and return its path, or None on failure.

    Extracts only ffmpeg.exe (~80 MB) from the gyan.dev essentials build.
    Stores it in {app}/bin/ffmpeg.exe (installed) or {exe_dir}/bin/ (portable).
    """
    bin_dir = _get_bin_dir()
    dest = bin_dir / "ffmpeg.exe"

    if dest.exists():
        _cache["path"] = str(dest)
        return str(dest)

    bin_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[FFMPEG] Downloading from %s", _FFMPEG_URL)

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    tmp_zip = Path(tmp_path)

    try:

        def _report(block_num: int, block_size: int, total_size: int) -> None:
            if total_size > 0 and progress_callback and hasattr(progress_callback, "configure"):
                downloaded = block_num * block_size
                pct = min(downloaded * 100 // total_size, 100)
                with contextlib.suppress(Exception):
                    progress_callback.configure(text=f"Downloading ffmpeg... {pct}%")

        urllib.request.urlretrieve(_FFMPEG_URL, str(tmp_zip), _report)  # noqa: S310

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

        if dest.exists() and dest.stat().st_size > 0:
            _cache["path"] = str(dest)
            logger.info("[FFMPEG] Downloaded successfully to %s", dest)
            return str(dest)

        logger.error("[FFMPEG] Downloaded file is empty")
        return None

    except Exception as e:
        logger.error("[FFMPEG] Download failed: %s", e)
        return None

    finally:
        tmp_zip.unlink(missing_ok=True)
        import os

        os.close(tmp_fd)


def ensure_ffmpeg_available(root_window: Tk | None = None) -> None:
    """Ensure ffmpeg is available, downloading in background if needed.

    If ffmpeg is missing and we're on Windows, starts a background thread
    to download it. Updates the status bar if root_window is provided.
    """
    if is_ffmpeg_available():
        return

    import threading

    label = None
    if (
        root_window is not None
        and hasattr(root_window, "status_bar")
        and hasattr(root_window.status_bar, "status_label")
    ):
        label = root_window.status_bar.status_label

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
