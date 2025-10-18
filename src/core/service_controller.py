"""Service controller for handling download operations."""

import logging
import os
import threading
import re
from pathlib import Path
from typing import List, Callable, Optional
import yt_dlp

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
        """Worker function to handle a single download using yt-dlp Python API."""
        logger.info(f"[SERVICE_CONTROLLER] download_worker called for: {download.name}")
        try:
            # Create sanitized directory name
            sanitized_name = re.sub(r'[^\w\s-]', '', download.name).strip()
            sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name)
            video_dir = Path(download_dir).expanduser() / sanitized_name
            video_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[SERVICE_CONTROLLER] Created video directory: {video_dir}")

            # Progress hook for yt-dlp
            def progress_hook(d):
                if progress_callback:
                    if d['status'] == 'downloading':
                        # Calculate progress percentage
                        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                        downloaded_bytes = d.get('downloaded_bytes', 0)
                        if total_bytes and total_bytes > 0:
                            progress = min(100, int((downloaded_bytes / total_bytes) * 100))
                            progress_callback(download, progress)
                    elif d['status'] == 'finished':
                        progress_callback(download, 100)

            # Build yt-dlp options with encoding fixes
            ydl_opts = {
                'progress_hooks': [progress_hook],
                'outtmpl': str(video_dir / f"{download.name}.%(ext)s"),
                'restrictfilenames': True,
                'no_warnings': True,
                'quiet': True,
                'ignoreerrors': False,
                'noplaylist': not getattr(download, 'download_playlist', False),
                # Encoding fixes
                'encoding': 'utf-8',
                'nocheckcertificate': True,
                'prefer_free_formats': True,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'ios', 'web'],  
                    }
                },
            }

            # Handle format selection
            format_type = getattr(download, 'format_type', 'video_audio')

            if getattr(download, 'audio_only', False):
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                })
            elif format_type == 'video_audio':
                # Video with audio combined
                if download.quality and download.quality != '720p':
                    height = download.quality[:-1]  # Remove 'p' from '720p'
                    ydl_opts['format'] = f"best[height<={height}]/best"
                else:
                    ydl_opts['format'] = 'best'
            elif format_type == 'video_only':
                # Video without audio
                if download.quality and download.quality != '720p':
                    height = download.quality[:-1]
                    ydl_opts['format'] = f"bestvideo[height<={height}]"
                else:
                    ydl_opts['format'] = 'bestvideo'
            elif format_type == 'separate':
                # Separate video and audio files
                if download.quality and download.quality != '720p':
                    height = download.quality[:-1]
                    ydl_opts['format'] = f"bestvideo[height<={height}]+bestaudio"
                else:
                    ydl_opts['format'] = 'bestvideo+bestaudio'
            else:
                # Default fallback
                if download.quality and download.quality != '720p':
                    height = download.quality[:-1]
                    ydl_opts['format'] = f"best[height<={height}]/best"
                else:
                    ydl_opts['format'] = 'best'

            # Handle subtitles
            if getattr(download, 'download_subtitles', False) and getattr(download, 'selected_subtitles'):
                subtitle_langs = [sub.get('language_code', 'en') for sub in download.selected_subtitles]
                ydl_opts.update({
                    'writesubtitles': True,
                    'subtitleslangs': subtitle_langs,
                    'writeautomaticsub': True,
                })

            # Handle thumbnails
            if getattr(download, 'download_thumbnail', True):
                ydl_opts['writethumbnail'] = True

            # Handle metadata embedding
            if getattr(download, 'embed_metadata', True):
                ydl_opts['embedmetadata'] = True

            # Handle cookies
            if getattr(download, 'cookie_path', None):
                ydl_opts['cookiefile'] = download.cookie_path
            elif getattr(download, 'selected_browser', None):
                # Note: Python API doesn't directly support cookies-from-browser
                # We'll need to extract cookies first or fall back to file
                pass

            # Simulate some initial progress since API might take time to start
            import time
            for progress in range(0, 30, 10):
                if progress_callback:
                    progress_callback(download, progress)
                time.sleep(0.1)

            # Download using yt-dlp Python API with encoding error handling
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([download.url])
            except UnicodeDecodeError as ude:
                # Try with different encoding options
                logger.warning(f"[SERVICE_CONTROLLER] Unicode decode error, trying fallback: {ude}")
                ydl_opts_fallback = ydl_opts.copy()
                ydl_opts_fallback.update({
                    'encoding': 'latin-1',
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios', 'android', 'tv_embedded', 'web'],
                            'player_skip': ['webpage'],
                            'skip': ['dash'],
                        }
                    },
                    'format': 'best[ext=mp4]/best',  # Simpler format selection
                })

                try:
                    with yt_dlp.YoutubeDL(ydl_opts_fallback) as ydl:
                        ydl.download([download.url])
                except Exception as fallback_e:
                    raise yt_dlp.utils.DownloadError(f"Fallback also failed: {fallback_e}") from fallback_e

            # Final progress update
            if progress_callback:
                progress_callback(download, 100)

            logger.info(f"[SERVICE_CONTROLLER] Download completed successfully: {download.name}")
            if completion_callback:
                completion_callback(True, f"Download completed: {download.name}")

        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(f"[SERVICE_CONTROLLER] {error_msg}")
            if completion_callback:
                completion_callback(False, error_msg)
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logger.error(f"[SERVICE_CONTROLLER] Download error for {download.name}: {e}")
            if completion_callback:
                completion_callback(False, error_msg)

    def has_active_downloads(self):
        """Check if there are active downloads."""
        with self._lock:
            return self._active_downloads > 0