from .base import BaseDownloader
import yt_dlp
import logging
import os
import time
from typing import Callable, Optional, Dict, Any
from pathlib import Path

from src.utils.common import sanitize_filename, check_site_connection

logger = logging.getLogger(__name__)

class YouTubeDownloader(BaseDownloader):
    """Downloader for YouTube videos."""

    def __init__(
            self,
            quality: str = "720p",
            download_playlist: bool = False,
            audio_only: bool = False
    ):
        self.quality = quality
        self.download_playlist = download_playlist
        self.audio_only = audio_only
        self.ytdl_opts = self._get_ytdl_options()

    def _get_ytdl_options(self) -> Dict[str, Any]:
        """Generate yt-dlp options based on current settings."""
        options = {
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'format_sort': ['res'],
            'retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {'fragment': lambda x: 3 * (x + 1)},
            'socket_timeout': 15,
            'extractor_retries': 3,
            'hls_prefer_native': True,
            'nocheckcertificate': True,
            # Add a user agent to avoid some blocks
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

        # Set format based on quality and audio_only options
        if self.audio_only:
            options['format'] = 'bestaudio/best'
            options['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            if self.quality == "highest":
                options['format'] = 'bestvideo+bestaudio/best'
            elif self.quality == "lowest":
                options['format'] = 'worstvideo+worstaudio/worst'
            else:
                # Try to match requested quality
                res = self.quality.replace('p', '')
                try:
                    height = int(res)
                    options['format'] = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]'
                except ValueError:
                    # Default to 720p if quality is not a valid number
                    options['format'] = 'bestvideo[height<=720]+bestaudio/best[height<=720]'

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
            sanitized_name = sanitize_filename(base_filename)
            
            # Extension depends on audio_only setting
            ext = '.mp3' if self.audio_only else '.mp4'
            output_template = os.path.join(save_dir, sanitized_name)
            
            # Prepare options with output path
            opts = self.ytdl_opts.copy()
            opts.update({
                'outtmpl': {'default': output_template + ext},
            })
            
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