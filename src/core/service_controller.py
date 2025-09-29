"""Service controller for handling download operations."""

import logging
import os
import threading
import subprocess
import re
import locale
import codecs
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

            # Add encoding-friendly options first - avoid encoding issues
            cmd.extend([
                '--no-check-certificate',  # Avoid SSL issues that might cause encoding problems
                '--ignore-errors',  # Continue on errors
                '--no-warnings',  # Reduce noise in output
                '--restrict-filenames',  # Avoid special characters in filenames
                '--no-progress',  # Avoid progress bar control sequences
                '--newline',  # Use consistent newlines
            ])

            # Add quality/format options - handle video_audio format more carefully
            format_type = getattr(download, 'format_type', 'video_audio')
            
            if getattr(download, 'audio_only', False):
                cmd.extend(['-x', '--audio-format', 'mp3'])
            elif format_type == 'video_audio':
                # For video_audio, use a simpler format selection that's less likely to cause encoding issues
                if download.quality and download.quality != '720p':
                    cmd.extend(['-f', f"best[height<={download.quality[:-1]}]/best"])
                else:
                    cmd.extend(['-f', 'best'])
            elif format_type == 'video_only':
                if download.quality and download.quality != '720p':
                    cmd.extend(['-f', f"bestvideo[height<={download.quality[:-1]}]"])
                else:
                    cmd.extend(['-f', 'bestvideo'])
            elif format_type == 'separate':
                if download.quality and download.quality != '720p':
                    cmd.extend(['-f', f"bestvideo[height<={download.quality[:-1]}]+bestaudio"])
                else:
                    cmd.extend(['-f', 'bestvideo+bestaudio'])
            else:
                # Default fallback
                if download.quality and download.quality != '720p':
                    cmd.extend(['-f', f"best[height<={download.quality[:-1]}]"])
                else:
                    cmd.extend(['-f', 'best'])

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

            # Run yt-dlp with comprehensive encoding handling
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            env['LANG'] = 'en_US.UTF-8'
            env['LC_ALL'] = 'en_US.UTF-8'
            env['LC_CTYPE'] = 'en_US.UTF-8'
            env['LC_NUMERIC'] = 'en_US.UTF-8'
            env['LC_TIME'] = 'en_US.UTF-8'
            env['LC_COLLATE'] = 'en_US.UTF-8'
            env['LC_MONETARY'] = 'en_US.UTF-8'
            env['LC_MESSAGES'] = 'en_US.UTF-8'
            env['LC_PAPER'] = 'en_US.UTF-8'
            env['LC_NAME'] = 'en_US.UTF-8'
            env['LC_ADDRESS'] = 'en_US.UTF-8'
            env['LC_TELEPHONE'] = 'en_US.UTF-8'
            env['LC_MEASUREMENT'] = 'en_US.UTF-8'
            env['LC_IDENTIFICATION'] = 'en_US.UTF-8'
            # Force UTF-8 for all text processing
            env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
            env['PYTHONIOENCODING'] = 'utf-8'

            try:
                # Use bytes approach first, then decode manually to avoid encoding issues
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=3600,
                    env=env
                )

                # Get system preferred encoding and decode with surrogateescape
                try:
                    encoding = locale.getpreferredencoding(False)
                    stdout = result.stdout.decode(encoding, errors='surrogateescape')
                    stderr = result.stderr.decode(encoding, errors='surrogateescape')
                except Exception:
                    # Fallback to safe decode if locale approach fails
                    stdout = self._safe_decode_bytes(result.stdout)
                    stderr = self._safe_decode_bytes(result.stderr)

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
                # Handle error output - already decoded safely
                stderr_output = stderr if stderr else ""
                stdout_output = stdout if stdout else ""

                # Check if this is a UTF-8 encoding error and try alternative clients
                if "0xb0" in stderr_output or "utf-8" in stderr_output.lower() or "invalid start byte" in stderr_output:
                    logger.warning(f"[SERVICE_CONTROLLER] UTF-8 encoding error detected, trying alternative approach: {download.name}")

                    # Try with different clients that handle encoding better
                    for client in ['ios', 'android', 'tv_embedded', 'web']:
                        try:
                            cmd_alt = self._build_alternative_command(cmd, download, video_dir, client)
                            logger.info(f"[SERVICE_CONTROLLER] Trying {client} client for: {download.name}")

                            result_alt = subprocess.run(
                                cmd_alt,
                                capture_output=True,
                                timeout=3600,
                                env=env
                            )

                            if result_alt.returncode == 0:
                                logger.info(f"[SERVICE_CONTROLLER] Download completed successfully with {client} client: {download.name}")
                                if completion_callback:
                                    completion_callback(True, f"Download completed: {download.name}")
                                return
                            else:
                                # Decode alternative result safely
                                try:
                                    alt_stderr = result_alt.stderr.decode(locale.getpreferredencoding(False), errors='surrogateescape')
                                except Exception:
                                    alt_stderr = self._safe_decode_bytes(result_alt.stderr)
                                logger.warning(f"[SERVICE_CONTROLLER] {client} client failed: {alt_stderr[:200]}")
                        except Exception as client_e:
                            logger.warning(f"[SERVICE_CONTROLLER] {client} client attempt failed: {client_e}")

                # Combine both outputs for complete error information
                error_output = f"STDERR: {stderr_output}"
                if stdout_output.strip():
                    error_output += f"\nSTDOUT: {stdout_output}"

                logger.error(f"[SERVICE_CONTROLLER] Download failed: {download.name}")
                logger.error(f"[SERVICE_CONTROLLER] Error output: {error_output}")
                if completion_callback:
                    completion_callback(False, f"Download failed: {error_output}")

        except Exception as e:
            logger.error(f"[SERVICE_CONTROLLER] Download error for {download.name}: {e}")
            if completion_callback:
                completion_callback(False, f"Download error: {str(e)}")

    def _build_alternative_command(self, original_cmd, download, video_dir, client):
        """Build an alternative command with different client."""
        cmd_alt = ['.venv/bin/yt-dlp']

        # Basic encoding-friendly options
        cmd_alt.extend([
            '--no-check-certificate',
            '--ignore-errors',
            '--no-warnings',
            '--extractor-args', f'youtube:player_client={client}',
            '--extractor-args', 'youtube:player_skip=webpage',
            '--extractor-args', 'youtube:skip=dash',
            '-f', 'best',  # Use simplest format selection
        ])

        # Add the same options as before
        if getattr(download, 'audio_only', False):
            cmd_alt.extend(['-x', '--audio-format', 'mp3'])

        if getattr(download, 'download_playlist', False):
            cmd_alt.append('--yes-playlist')
        else:
            cmd_alt.append('--no-playlist')

        if getattr(download, 'download_thumbnail', True):
            cmd_alt.append('--write-thumbnail')

        if getattr(download, 'embed_metadata', True):
            cmd_alt.append('--embed-metadata')

        if getattr(download, 'cookie_path', None):
            cmd_alt.extend(['--cookies', download.cookie_path])
        elif getattr(download, 'selected_browser', None):
            cmd_alt.extend(['--cookies-from-browser', download.selected_browser])

        cmd_alt.extend(['-o', str(video_dir / f"{download.name}.%(ext)s")])
        cmd_alt.append(download.url)

        return cmd_alt

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

        # Try cp1252 (common on Windows systems)
        try:
            return byte_data.decode('cp1252')
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