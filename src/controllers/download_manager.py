# src/controllers/download_manager.py

import threading
import logging
from typing import List, Callable, Optional, Dict, Any
from urllib.parse import urlparse

from src.models.download_item import DownloadItem
from src.downloaders.youtube import YouTubeDownloader
from src.downloaders.twitter import TwitterDownloader
from src.downloaders.instagram import InstagramDownloader
from src.downloaders.pinterest import PinterestDownloader
from src.downloaders.pinterest import PinterestDownloader

logger = logging.getLogger(__name__)

class DownloadManager:
    """Manages download operations and state."""

    def __init__(self):
        self.items: List[DownloadItem] = []
        self.active_downloads = 0
        self.youtube_downloader = YouTubeDownloader()
        self.twitter_downloader = TwitterDownloader()
        self.pinterest_downloader = PinterestDownloader()
        self._lock = threading.Lock()
        self.auth_manager = None
        self.youtube_options = {
            'quality': '720p',
            'playlist': None,
            'audio_only': None
        }
    def set_quality(self, quality: str) -> None:
        """Set video quality."""
        self.youtube_options['quality'] = quality
        self.youtube_downloader = YouTubeDownloader(
            quality=quality,
        )

    def set_option(self, option: str, value: bool) -> None:
        """Set download option."""
        if option in ['playlist', 'audio_only']:
            self.youtube_options[option] = value
            self.youtube_downloader = YouTubeDownloader(
                download_playlist=bool(self.youtube_options['playlist']),
                audio_only=bool(self.youtube_options['audio_only'])
            )
    def set_auth_manager(self, auth_manager: Any):
        """Set the authentication manager instance."""
        self.auth_manager = auth_manager

    def add_item(self, item: DownloadItem) -> None:
        with self._lock:
            self.items.append(item)

    def remove_items(self, indices: List[int]) -> None:
        with self._lock:
            for index in sorted(indices, reverse=True):
                if 0 <= index < len(self.items):
                    self.items.pop(index)

    def clear_items(self) -> None:
        with self._lock:
            self.items.clear()

    def get_items(self) -> List[DownloadItem]:
        with self._lock:
            return self.items.copy()

    def start_downloads(
            self,
            download_dir: str,
            progress_callback: Callable[[DownloadItem, float], None],
            completion_callback: Callable[[bool, Optional[str]], None]
    ) -> None:
        def download_worker():
            try:
                with self._lock:
                    items_to_download = [item for item in self.items if item.status == "Pending"]

                for item in items_to_download:
                    item.status = "Downloading"

                    def item_progress(progress: float):
                        progress_callback(item, progress)

                    success = self._download_item(
                        item,
                        download_dir,
                        item_progress
                    )
                    item.status = "Completed" if success else "Failed"

                completion_callback(True)
            except Exception as e:
                logger.error(f"Download worker error: {str(e)}")
                completion_callback(False, str(e))

        threading.Thread(target=download_worker, daemon=True).start()

    def _download_item(
            self,
            item: DownloadItem,
            download_dir: str,
            progress_callback: Callable[[float, float], None]
    ) -> bool:
        try:
            domain = urlparse(item.url).netloc.lower()
            save_path = f"{download_dir}/{item.name}"

            if 'youtube.com' in domain:
                return self.youtube_downloader.download(item.url, save_path, progress_callback)
            elif 'twitter.com' in domain or 'x.com' in domain:
                return self.twitter_downloader.download(item.url, save_path, progress_callback)
            elif 'instagram.com' in domain:
                if not self.auth_manager:
                    raise ValueError("Authentication manager not set")

                instagram_downloader = self.auth_manager.get_instagram_downloader()
                if not instagram_downloader:
                    raise ValueError("Instagram authentication required")

                return instagram_downloader.download(item.url, save_path, progress_callback)
            elif 'pinterest.com' in domain:
                return self.pinterest_downloader.download(item.url, save_path, progress_callback)
            else:
                logger.error(f"Unsupported domain: {domain}")
                return False

        except Exception as e:
            logger.error(f"Error downloading {item.name}: {str(e)}")
            return False

