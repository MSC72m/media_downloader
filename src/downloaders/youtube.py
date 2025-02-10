from .base import BaseDownloader
import yt_dlp
import logging
import os
from typing import Callable, Optional

from ..schemas.schemas import YtOptions

logger = logging.getLogger(__name__)

class YouTubeDownloader(BaseDownloader):
    def __init__(self, options: YtOptions):
        self.quality = options.quality
        self.download_playlist = options.download_playlist
        self.audio_only = options.audio_only
        self.subtitle_setting = options.subtitle_setting

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
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

            if progress_callback:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        total = d.get('total_bytes', d.get('total_bytes_estimate', 0))
                        downloaded = d.get('downloaded_bytes', 0)
                        speed = d.get('speed', 0)
                        if total > 0:
                            progress = (downloaded / total) * 100
                            progress_callback(progress, speed)

                ydl_opts['progress_hooks'] = [progress_hook]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True

        except Exception as e:
            logger.error(f"Error downloading from YouTube: {str(e)}", exc_info=True)
            return False