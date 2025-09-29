"""Service controller for handling download operations."""

import logging
import os
import threading
import subprocess
import re
from pathlib import Path
from typing import List, Callable, Optional

logger = logging.getLogger(__name__)


class ServiceController:
    """Controller for managing download operations."""

    def __init__(self, download_service, cookie_manager):
        self.download_service = download_service
        self.cookie_manager = cookie_manager
        self._active_downloads = 0
        self._lock = threading.Lock()

    def start_downloads(self, downloads, progress_callback=None, completion_callback=None):
        """Start downloads with proper UI feedback using yt-dlp directly."""
        logger.info(f"[SERVICE_CONTROLLER] start_downloads called with {len(downloads)} downloads")

        if not downloads:
            logger.warning("[SERVICE_CONTROLLER] No downloads to start")
            if completion_callback:
                completion_callback(True, "No downloads to process")
            return

        try:
            # Start each download in a separate thread
            for download in downloads:
                download_dir = getattr(download, 'output_path', '~/Downloads') or '~/Downloads'

                # Start download thread
                thread = threading.Thread(
                    target=self._download_worker,
                    args=(download, download_dir, progress_callback, completion_callback),
                    daemon=True
                )
                thread.start()
                logger.info(f"[SERVICE_CONTROLLER] Started download thread for {download.name}")

            logger.info("[SERVICE_CONTROLLER] All download threads started")

        except Exception as e:
            logger.error(f"[SERVICE_CONTROLLER] Error starting downloads: {e}")
            if completion_callback:
                completion_callback(False, f"Error starting downloads: {e}")

    def _download_worker(self, download, download_dir, progress_callback, completion_callback):
        """Worker function to handle a single download."""
        logger.info(f"[SERVICE_CONTROLLER] download_worker called for: {download.name}")
        try:
            # Create sanitized directory name
            sanitized_name = re.sub(r'[^\w\s-]', '', download.name).strip()
            sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name)
            video_dir = Path(download_dir).expanduser() / sanitized_name
            video_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[SERVICE_CONTROLLER] Created video directory: {video_dir}")

            # Build yt-dlp command
            cmd = ['.venv/bin/yt-dlp']

            # Add quality/format options
            if download.quality and download.quality != '720p':
                cmd.extend(['-f', f"bestvideo[height<={download.quality[:-1]}]+bestaudio/best[height<={download.quality[:-1]}]"])

            # Add audio-only option
            if getattr(download, 'audio_only', False):
                cmd.extend(['-x', '--audio-format', 'mp3'])

            # Add playlist option
            if getattr(download, 'download_playlist', False):
                cmd.append('--yes-playlist')
            else:
                cmd.append('--no-playlist')

            # Add subtitle options
            if getattr(download, 'download_subtitles', False) and getattr(download, 'selected_subtitles'):
                # Add selected subtitles
                for sub in download.selected_subtitles:
                    lang = sub.get('language_code', 'en')
                    cmd.extend(['--write-subs', '--sub-lang', lang])

            # Add thumbnail option
            if getattr(download, 'download_thumbnail', True):
                cmd.append('--write-thumbnail')

            # Add metadata option
            if getattr(download, 'embed_metadata', True):
                cmd.append('--embed-metadata')

            # Add cookie options
            if getattr(download, 'cookie_path', None):
                cmd.extend(['--cookies', download.cookie_path])
            elif getattr(download, 'selected_browser', None):
                cmd.extend(['--cookies-from-browser', download.selected_browser])

            # Add output path - use sanitized directory
            cmd.extend(['-o', str(video_dir / f"{download.name}.%(ext)s")])

            # Add the URL
            cmd.append(download.url)

            # Simulate progress updates since subprocess.run is blocking
            import time
            for progress in range(0, 101, 10):
                if progress_callback:
                    progress_callback(download, progress)
                time.sleep(0.1)  # Reduced sleep time for faster simulation

            # Run yt-dlp with proper encoding handling
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            env['LANG'] = 'en_US.UTF-8'
            env['LC_ALL'] = 'en_US.UTF-8'

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=3600,
                    env=env
                )
            except subprocess.TimeoutExpired:
                error_msg = "Download timed out after 1 hour"
                logger.error(f"[SERVICE_CONTROLLER] {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)
                return
            except Exception as e:
                error_msg = f"Subprocess error: {str(e)}"
                logger.error(f"[SERVICE_CONTROLLER] {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)
                return

            # Final progress update
            if progress_callback:
                progress_callback(download, 100)

            if result.returncode == 0:
                logger.info(f"[SERVICE_CONTROLLER] Download completed successfully: {download.name}")
                if completion_callback:
                    completion_callback(True, f"Download completed: {download.name}")
            else:
                # Handle error output - decode with proper error handling
                error_output = self._safe_decode_bytes(result.stderr)

                logger.error(f"[SERVICE_CONTROLLER] Download failed: {download.name}")
                logger.error(f"[SERVICE_CONTROLLER] Error output: {error_output}")
                if completion_callback:
                    completion_callback(False, f"Download failed: {error_output}")

        except Exception as e:
            logger.error(f"[SERVICE_CONTROLLER] Download error for {download.name}: {e}")
            if completion_callback:
                completion_callback(False, f"Download error: {str(e)}")

    def _safe_decode_bytes(self, byte_data: bytes) -> str:
        """Safely decode bytes with multiple fallback encodings."""
        if not byte_data:
            return ""

        # Try UTF-8 first (most common)
        try:
            return byte_data.decode('utf-8')
        except UnicodeDecodeError:
            pass

        # Try latin-1 (handles all byte values)
        try:
            return byte_data.decode('latin-1')
        except UnicodeDecodeError:
            pass

        # Final fallback: replace problematic characters
        try:
            return byte_data.decode('utf-8', errors='replace')
        except Exception:
            # Last resort: use repr to show raw bytes
            return repr(byte_data)

    def has_active_downloads(self):
        """Check if there are active downloads."""
        with self._lock:
            return self._active_downloads > 0