"""Centralized ffmpeg detection and path resolution.

Single source of truth for all ffmpeg lookups across the application.
Search order:
  1. Next to the running exe  ({app}/bin/ffmpeg.exe — installed)
  2. Inside PyInstaller _internal/  (portable bundle)
  3. System PATH
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

_cache: dict[str, str | None] = {}


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
