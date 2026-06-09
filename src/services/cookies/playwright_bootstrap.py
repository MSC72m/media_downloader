"""Playwright bootstrap utilities for first-run Chromium installation.

When the application is distributed as a PyInstaller bundle, the Playwright
Python package is included but the Chromium browser binary is NOT bundled
(it's ~150-200 MB and updates frequently). This module detects whether
Chromium is available and, if not, downloads it automatically on first
launch -- showing a progress dialog to the user.
"""

from __future__ import annotations

import contextlib
import importlib.util
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.utils.logger import get_logger

if TYPE_CHECKING:
    import tkinter as tk

logger = get_logger(__name__)

# Module-level event that signals when Chromium is ready for use.
# Cookie generators should wait on this before attempting to launch browsers.
_chromium_ready = threading.Event()
_chromium_check_done = threading.Event()


def wait_for_chromium(timeout: float = 120.0) -> bool:
    """Block until Chromium install is complete or timeout.

    Returns True if Chromium is available.
    """
    _chromium_check_done.wait(timeout=timeout)
    return _chromium_ready.is_set()


# Regex patterns to extract progress from ``playwright install`` output.
# Playwright CLI emits lines like:
#   "Downloading Chromium 120.0.6099.28 (playwright build v1091) - 150.2 Mb"
#   " 45.3 Mb [=======>              ] 30% ..."
#   "Chromium 120.0.6099.28 ... downloaded to ..."
_RE_DOWNLOAD_START = re.compile(
    r"Downloading\s+(Chromium[\w\s.]*)\s*[-–]\s*([\d.]+\s*[MmGg][Bb])",
    re.IGNORECASE,
)
_RE_PROGRESS_PCT = re.compile(r"(\d{1,3})%")
_RE_PROGRESS_MB = re.compile(r"([\d.]+)\s*[MmGg][Bb]")
_RE_DOWNLOADED = re.compile(r"downloaded\s+to", re.IGNORECASE)


def is_playwright_installed() -> bool:
    """Check whether the ``playwright`` Python package is importable."""
    return importlib.util.find_spec("playwright") is not None


def _playwright_cli_command(*args: str) -> list[str]:
    """Return a Playwright CLI command that works in normal and frozen builds.

    In a PyInstaller executable, ``sys.executable`` points at MediaDownloader.exe.
    Running ``sys.executable -m playwright ...`` would recursively launch the app.
    Playwright ships its own Node driver, so call that directly instead.
    """
    from playwright._impl._driver import compute_driver_executable

    node_exe, cli_js = compute_driver_executable()
    return [str(node_exe), str(cli_js), *args]


def is_chromium_installed() -> bool:
    """Check whether Playwright's managed Chromium binary exists on disk.

    This avoids launching a full browser just to check -- instead it
    inspects the Playwright browser registry path directly.
    """
    if not is_playwright_installed():
        return False

    try:
        # Playwright stores browsers under a well-known directory.
        # The canonical way to find it is via the internal registry,
        # but we can also just attempt a lightweight CLI check.
        result = subprocess.run(
            _playwright_cli_command("install", "--dry-run", "chromium"),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        # If dry-run exits 0 and mentions "already installed", we're good
        combined = (result.stdout + result.stderr).lower()
        if result.returncode == 0 and "already installed" in combined:
            return True

        # Fallback: check the browser path directly
        return _check_browser_path()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return _check_browser_path()


def _get_browser_search_bases() -> list[Path]:
    """Return directories to search for Playwright browser binaries."""
    bases: list[Path] = []

    # PyInstaller frozen bundle: browsers under _internal/playwright/driver/package/.local-browsers/
    if getattr(sys, "frozen", False):
        internal = (
            Path(sys._MEIPASS)
            if hasattr(sys, "_MEIPASS")
            else Path(sys.executable).parent / "_internal"
        )
        bases.append(internal / "playwright" / "driver" / "package" / ".local-browsers")

    # Standard Playwright locations
    if sys.platform == "win32":
        bases.append(Path.home() / "AppData" / "Local" / "ms-playwright")
    elif sys.platform == "darwin":
        bases.append(Path.home() / "Library" / "Caches" / "ms-playwright")
    else:
        bases.append(Path.home() / ".cache" / "ms-playwright")

    return bases


def _get_browser_executable_candidates(browser_dir: Path) -> list[Path]:
    """Return known browser executable paths for a given browser directory."""
    if sys.platform == "win32":
        return [
            browser_dir / "chrome-win" / "chrome.exe",
            browser_dir / "chrome-win64" / "chrome.exe",
            browser_dir / "chrome-headless-shell-win64" / "chrome-headless-shell.exe",
        ]
    if sys.platform == "darwin":
        return [
            browser_dir / "chrome-mac" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
            browser_dir / "chrome-mac-arm64" / "Chromium.app" / "Contents" / "MacOS" / "Chromium",
        ]
    return [
        browser_dir / "chrome-linux" / "chrome",
        browser_dir / "chrome-linux64" / "chrome",
    ]


def _check_browser_path() -> bool:
    """Inspect the filesystem for Playwright's Chromium binary."""
    try:
        for base in _get_browser_search_bases():
            if not base.exists():
                continue

            for child in base.iterdir():
                if not child.is_dir() or "chromium" not in child.name.lower():
                    continue

                for exe in _get_browser_executable_candidates(child):
                    if exe.exists():
                        logger.info(f"[PLAYWRIGHT_BOOTSTRAP] Found Chromium at {exe}")
                        return True
        return False
    except OSError:
        return False


class _InstallProgress:
    """Thread-safe container for install progress state."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.phase: str = "Preparing..."
        self.percent: int | None = None
        self.total_size: str = ""
        self.downloaded_mb: float = 0.0
        self.done: bool = False
        self.success: bool = False
        self.error_message: str = ""

    def set_phase(self, phase: str) -> None:
        with self.lock:
            self.phase = phase

    def set_percent(self, pct: int) -> None:
        with self.lock:
            self.percent = min(pct, 100)

    def set_total_size(self, size: str) -> None:
        with self.lock:
            self.total_size = size

    def set_downloaded(self, mb: float) -> None:
        with self.lock:
            self.downloaded_mb = mb

    def finish(self, success: bool, error: str = "") -> None:
        with self.lock:
            self.done = True
            self.success = success
            self.error_message = error

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "phase": self.phase,
                "percent": self.percent,
                "total_size": self.total_size,
                "downloaded_mb": self.downloaded_mb,
                "done": self.done,
                "success": self.success,
                "error_message": self.error_message,
            }


def install_chromium_streaming(progress: _InstallProgress) -> None:
    """Download Chromium via ``playwright install chromium``, streaming output.

    Parses stdout/stderr line-by-line to extract download percentage and
    updates ``progress`` in real time so the GUI can reflect it.
    """
    try:
        logger.info("[PLAYWRIGHT_BOOTSTRAP] Starting Chromium installation (streaming)...")
        progress.set_phase("Starting Chromium download...")

        proc = subprocess.Popen(
            _playwright_cli_command("install", "chromium"),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line-buffered
        )

        assert proc.stdout is not None  # for type checker
        deadline = time.monotonic() + 300  # 5 minute timeout

        for raw_line in proc.stdout:
            if time.monotonic() > deadline:
                proc.kill()
                progress.finish(
                    False,
                    "Download timed out after 5 minutes. Check your internet connection.",
                )
                return

            line = raw_line.strip()
            if not line:
                continue

            logger.debug(f"[PLAYWRIGHT_BOOTSTRAP] >> {line}")

            # Detect download start — extract total size
            m_start = _RE_DOWNLOAD_START.search(line)
            if m_start:
                progress.set_total_size(m_start.group(2).strip())
                progress.set_phase(f"Downloading {m_start.group(1).strip()}...")
                continue

            # Detect percentage
            m_pct = _RE_PROGRESS_PCT.search(line)
            if m_pct:
                pct = int(m_pct.group(1))
                progress.set_percent(pct)

                # Also try to grab the current MB downloaded
                m_mb = _RE_PROGRESS_MB.search(line)
                if m_mb:
                    with contextlib.suppress(ValueError):
                        progress.set_downloaded(float(m_mb.group(1)))
                continue

            # Detect completion message
            if _RE_DOWNLOADED.search(line):
                progress.set_percent(100)
                progress.set_phase("Download complete. Installing...")
                continue

        proc.wait(timeout=30)

        if proc.returncode == 0:
            logger.info("[PLAYWRIGHT_BOOTSTRAP] Chromium installed successfully")
            progress.finish(True)
        else:
            error = f"Process exited with code {proc.returncode}"
            logger.error(f"[PLAYWRIGHT_BOOTSTRAP] {error}")
            progress.finish(False, error)

    except subprocess.TimeoutExpired:
        msg = "Chromium download timed out. Check your internet connection."
        logger.error(f"[PLAYWRIGHT_BOOTSTRAP] {msg}")
        progress.finish(False, msg)

    except FileNotFoundError:
        msg = "Could not find Python executable to run Playwright installer."
        logger.error(f"[PLAYWRIGHT_BOOTSTRAP] {msg}")
        progress.finish(False, msg)

    except Exception as e:
        msg = f"Unexpected error installing Chromium: {e}"
        logger.error(f"[PLAYWRIGHT_BOOTSTRAP] {msg}", exc_info=True)
        progress.finish(False, msg)


def install_chromium_blocking() -> tuple[bool, str]:
    """Download and install Chromium (blocking, no GUI).

    Returns:
        A tuple of (success, message).
    """
    progress = _InstallProgress()
    install_chromium_streaming(progress)
    snap = progress.snapshot()
    if snap["success"]:
        return True, "Chromium browser installed successfully."
    return False, str(snap["error_message"]) or "Unknown error during installation."


def install_chromium_with_dialog(root_window: tk.Tk | None = None) -> bool:
    """Install Chromium with a GUI progress dialog.

    If ``root_window`` is a CTk/Tk window, shows a modal dialog during
    download with real-time progress. Otherwise falls back to a blocking
    install with console output.

    Returns:
        True if Chromium was installed successfully.
    """
    if root_window is None:
        success, msg = install_chromium_blocking()
        if not success:
            logger.error(f"[PLAYWRIGHT_BOOTSTRAP] {msg}")
        return success

    try:
        import customtkinter as ctk
    except ImportError:
        success, msg = install_chromium_blocking()
        return success

    # Shared progress state
    progress = _InstallProgress()

    # ── Build modal dialog ────────────────────────────────────────────
    dialog = ctk.CTkToplevel(root_window)
    dialog.title("Setting Up Browser")
    dialog.geometry("520x230")
    dialog.resizable(False, False)
    dialog.transient(root_window)
    dialog.grab_set()

    # Center on parent
    dialog.update_idletasks()
    x = root_window.winfo_x() + (root_window.winfo_width() // 2) - 260
    y = root_window.winfo_y() + (root_window.winfo_height() // 2) - 115
    dialog.geometry(f"520x230+{x}+{y}")

    frame = ctk.CTkFrame(dialog, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=24, pady=20)

    title_label = ctk.CTkLabel(
        frame,
        text="First-Time Setup",
        font=("Arial", 18, "bold"),
    )
    title_label.pack(pady=(0, 8))

    status_label = ctk.CTkLabel(
        frame,
        text="Preparing to download Chromium browser...\nThis only needs to happen once.",
        font=("Arial", 12),
    )
    status_label.pack(pady=(0, 8))

    # Determinate progress bar (0-1 range)
    progress_bar = ctk.CTkProgressBar(frame, mode="determinate", width=440)
    progress_bar.pack(pady=(0, 4))
    progress_bar.set(0)

    detail_label = ctk.CTkLabel(
        frame,
        text="",
        font=("Arial", 11),
        text_color="gray",
    )
    detail_label.pack(pady=(0, 8))

    # Prevent closing during install
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)

    # ── Poll progress from the background thread ──────────────────────
    def _poll_progress() -> None:
        snap = progress.snapshot()

        if snap["done"]:
            _on_complete(bool(snap["success"]), str(snap["error_message"]))
            return

        # Update status text
        phase = str(snap["phase"])
        status_label.configure(text=f"{phase}\nThis only needs to happen once.")

        # Update progress bar
        pct = snap["percent"]
        if pct is not None:
            progress_bar.configure(mode="determinate")
            progress_bar.set(int(pct) / 100.0)
            total = str(snap["total_size"])
            if total:
                detail_label.configure(text=f"{pct}% of {total}")
            else:
                detail_label.configure(text=f"{pct}%")
        else:
            # Still in preparation phase — pulse indeterminate
            progress_bar.configure(mode="indeterminate")
            progress_bar.start()

        dialog.after(200, _poll_progress)

    def _on_complete(success: bool, error: str) -> None:
        if success:
            progress_bar.configure(mode="determinate")
            progress_bar.set(1.0)
            status_label.configure(text="Chromium installed successfully!\nStarting application...")
            detail_label.configure(text="")
            dialog.after(1200, dialog.destroy)
        else:
            progress_bar.stop()
            progress_bar.configure(mode="determinate")
            progress_bar.set(0)
            status_label.configure(text=f"Installation failed:\n{error}")
            detail_label.configure(text="The app will continue but cookie generation may not work.")
            # Allow the user to dismiss
            dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
            close_btn = ctk.CTkButton(frame, text="Continue", command=dialog.destroy, width=120)
            close_btn.pack(pady=(4, 0))

    # ── Kick off install thread + polling ──────────────────────────────
    install_thread = threading.Thread(
        target=install_chromium_streaming,
        args=(progress,),
        daemon=True,
    )
    install_thread.start()

    dialog.after(200, _poll_progress)
    dialog.wait_window()

    snap = progress.snapshot()
    return bool(snap["success"])


def ensure_playwright_ready(root_window: tk.Tk | None = None) -> bool:
    """Ensure Playwright + Chromium are ready to use.

    Call this at application startup. If the Playwright Python package is
    available but Chromium hasn't been downloaded yet, it will
    automatically install it (with a progress dialog if a GUI window is
    provided).

    Signals the ``_chromium_ready`` event when complete so that cookie
    generator threads can wait before launching browsers.

    Returns:
        True if Playwright and Chromium are both available.
    """
    try:
        if not is_playwright_installed():
            logger.warning("[PLAYWRIGHT_BOOTSTRAP] Playwright Python package not available")
            _chromium_check_done.set()
            return False

        if is_chromium_installed():
            logger.info("[PLAYWRIGHT_BOOTSTRAP] Chromium is already installed")
            _chromium_ready.set()
            _chromium_check_done.set()
            return True

        logger.info("[PLAYWRIGHT_BOOTSTRAP] Chromium not found, starting installation...")
        result = install_chromium_with_dialog(root_window)
        if result:
            _chromium_ready.set()
        return result
    finally:
        _chromium_check_done.set()
