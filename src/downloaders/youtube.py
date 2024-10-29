import yt_dlp
from tkinter import messagebox
import logging
import os
from typing import Callable, Optional



logger = logging.getLogger(__name__)


class YouTubeDownloader:
    def __init__(self, quality: str = '720p', download_playlist: bool = False, audio_only: bool = False):
        self.quality = quality
        self.download_playlist = download_playlist
        self.audio_only = audio_only

    def download(
            self,
            url: str,
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]] = None,
    ) -> bool:
        try:
            ydl_opts = {
                'outtmpl': {
                    'default': os.path.join(os.path.dirname(save_path), '%(title)s.%(ext)s')
                },
                'noplaylist': not self.download_playlist,
            }

            if self.audio_only:
                ydl_opts.update({
                    'format': 'bestaudio/best',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '256',
                    }],
                })
            else:
                quality_value = int(self.quality.rstrip('pP'))
                ydl_opts['format'] = f'bestvideo[height<={quality_value}]+bestaudio/best[height<={quality_value}]'

            # Add progress hook
            if progress_callback:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
                        downloaded = d.get('downloaded_bytes', 0)
                        if total > 0:
                            progress = (downloaded / total) * 100
                            progress_callback(progress)  # Only pass progress

                ydl_opts['progress_hooks'] = [progress_hook]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True

        except Exception as e:
            logger.error(f"Error downloading from YouTube: {str(e)}", exc_info=True)
            return False