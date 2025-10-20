"""YouTube downloader service implementation."""

from src.utils.logger import get_logger
import time
import os
from typing import Optional, Callable, Dict, Any
import yt_dlp

from ...core.base import BaseDownloader
from ..file.sanitizer import FilenameSanitizer
from src.services.network.checker import check_site_connection
from .cookie_detector import CookieManager
from .metadata_service import YouTubeMetadataService

logger = get_logger(__name__)


class YouTubeDownloader(BaseDownloader):
    """YouTube downloader service with cookie support."""

    def __init__(
        self,
        quality: str = "720p",
        download_playlist: bool = False,
        audio_only: bool = False,
        cookie_manager: Optional[CookieManager] = None
    ):
        self.quality = quality
        self.download_playlist = download_playlist
        self.audio_only = audio_only
        self.cookie_manager = cookie_manager
        self.metadata_service = YouTubeMetadataService()
        self.ytdl_opts = self._get_simple_ytdl_options()

    def _get_simple_ytdl_options(self) -> Dict[str, Any]:
        """Generate simple yt-dlp options without format specifications."""
        options = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {'fragment': lambda x: 3 * (x + 1)},
            'socket_timeout': 15,
            'extractor_retries': 3,
            'hls_prefer_native': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            # NO format specifications - let yt-dlp choose automatically
        }

        # Add cookie information if available
        if self.cookie_manager:
            cookie_info = self.cookie_manager.get_youtube_cookie_info()
            if cookie_info:
                options.update(cookie_info)
                logger.info("Using cookies for YouTube download")

        # Handle playlists
        if not self.download_playlist:
            options['noplaylist'] = True
            options['playlist_items'] = '1'

        return options

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Download a YouTube video.

        Args:
            url: YouTube URL to download
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        # Check connectivity to YouTube
        connected, error_msg = check_site_connection("YouTube")
        if not connected:
            logger.error(f"Cannot download from YouTube: {error_msg}")
            return False

        try:
            # Create the output directory if it doesn't exist
            save_dir = os.path.dirname(save_path)
            os.makedirs(save_dir, exist_ok=True)

            # Create a filename
            base_filename = os.path.basename(save_path)
            sanitizer = FilenameSanitizer()
            sanitized_name = sanitizer.sanitize_filename(base_filename)

            # Extension depends on audio_only setting
            ext = '.mp3' if self.audio_only else '.mp4'
            output_template = os.path.join(save_dir, sanitized_name)

            # Prepare options with output path
            opts = self.ytdl_opts.copy()
            opts.update({
                'outtmpl': {'default': output_template + ext},
            })

            # Add format selection based on quality and audio settings
            if self.audio_only:
                opts['format'] = 'bestaudio'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            else:
                # Use simple quality-based format selection
                if self.quality == "highest":
                    opts['format'] = 'best'
                elif self.quality == "lowest":
                    opts['format'] = 'worst'
                else:
                    # For specific qualities like 720p, 1080p, etc.
                    # Use a simple format that won't cause errors
                    opts['format'] = 'best'

            # Add progress hook if callback provided
            if progress_callback:
                opts['progress_hooks'] = [self._create_progress_hook(progress_callback)]

            logger.info(f"Downloading from YouTube: {url}")

            # Retry mechanism for network issues
            max_retries = 3
            retry_wait = 3  # seconds

            for attempt in range(max_retries):
                try:
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        if not info:
                            logger.error("No video information extracted from YouTube")
                            return False

                        # Success
                        logger.info(f"Successfully downloaded YouTube content to {output_template}{ext}")
                        return True

                except yt_dlp.utils.DownloadError as e:
                    error_msg = str(e)
                    logger.debug(f"YouTube download error: {error_msg}")

                    if "HTTP Error 429" in error_msg:
                        # Rate limiting - wait longer between retries
                        wait_time = retry_wait * (2 ** attempt)
                        logger.warning(f"YouTube rate limit hit, waiting {wait_time} seconds before retry")
                        time.sleep(wait_time)
                        continue
                    elif ("Connection refused" in error_msg or
                          "Network Error" in error_msg or
                          "Unable to download" in error_msg or
                          "Errno 111" in error_msg):
                        # Network-related errors
                        if attempt < max_retries - 1:
                            wait_time = retry_wait * (attempt + 1)
                            logger.warning(f"Network error downloading YouTube video, retry {attempt+1}/{max_retries} in {wait_time}s")
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Failed to download after {max_retries} attempts: {error_msg}")
                            return False
                    else:
                        # Other errors - provide user-friendly message
                        if "This video is unavailable" in error_msg:
                            logger.error("This YouTube video is unavailable or private")
                        elif "Video unavailable" in error_msg:
                            logger.error("This YouTube video has been removed or is private")
                        elif "Sign in to confirm your age" in error_msg:
                            logger.error("This YouTube video requires age verification")
                        else:
                            logger.error(f"YouTube download error: {error_msg}")
                        return False

                except Exception as e:
                    logger.error(f"Error downloading from YouTube: {str(e)}")
                    return False

            return False  # If we get here, all retries failed

        except Exception as e:
            logger.error(f"Unexpected error downloading from YouTube: {str(e)}")
            return False

    @staticmethod
    def _create_progress_hook(callback: Callable[[float, float], None]):
        """Create a progress hook function for yt-dlp."""
        start_time = time.time()

        def hook(d):
            if d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)

                if total > 0:
                    progress = (downloaded / total) * 100
                else:
                    progress = 0

                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0

                callback(progress, speed)

            elif d['status'] == 'finished':
                callback(100, 0)

        return hook