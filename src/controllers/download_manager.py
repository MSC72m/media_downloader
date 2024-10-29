import threading
import logging
from typing import List, Callable, Optional, Dict, Any
from urllib.parse import urlparse
import os

from src.models.download_item import DownloadItem
from src.downloaders.youtube import YouTubeDownloader
from src.downloaders.twitter import TwitterDownloader
from src.downloaders.instagram import InstagramDownloader
from src.downloaders.pinterest import PinterestDownloader
from src.downloaders.pinterest import PinterestDownloader
from src.downloaders.base import BaseDownloader

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
            'playlist': False,
            'audio_only': False
        }

    def set_quality(self, quality: str) -> None:
        """Set video quality."""
        self.youtube_options['quality'] = quality
        self.youtube_downloader = YouTubeDownloader(
            quality=quality,
            download_playlist=self.youtube_options['playlist'],
            audio_only=self.youtube_options['audio_only']
        )

    def set_option(self, option: str, value: bool) -> None:
        """Set download option."""
        if option in ['playlist', 'audio_only']:
            self.youtube_options[option] = value
            self.youtube_downloader = YouTubeDownloader(
                quality=self.youtube_options['quality'],
                download_playlist=self.youtube_options['playlist'],
                audio_only=self.youtube_options['audio_only']
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

    def _get_downloader_for_url(self, url: str) -> Optional[BaseDownloader]:
        """Get the appropriate downloader for a URL."""
        domain = urlparse(url).netloc.lower()

        if any(x in domain for x in ['youtube.com', 'youtu.be']):
            return self.youtube_downloader
        elif any(x in domain for x in ['twitter.com', 'x.com']):
            return self.twitter_downloader
        elif any(x in domain for x in ['pinterest.com', 'pin.it']):
            return self.pinterest_downloader
        elif 'instagram.com' in domain:
            if not self.auth_manager or not self.auth_manager.is_instagram_authenticated():
                raise ValueError("Instagram authentication required")
            return self.auth_manager.get_instagram_downloader()
        return None

    def _download_item(
            self,
            item: DownloadItem,
            download_dir: str,
            progress_callback: Callable[[float], None]
    ) -> bool:
        try:
            save_path = os.path.join(download_dir, item.name)

            downloader = self._get_downloader_for_url(item.url)
            if not downloader:
                raise ValueError(f"Unsupported URL: {item.url}")

            def progress_wrapper(progress: float, speed: float = 0):
                if progress_callback:
                    progress_callback(progress)

            return downloader.download(item.url, save_path, progress_wrapper)

        except Exception as e:
            logger.error(f"Error downloading {item.name}: {str(e)}")
            return False

    def start_downloads(
            self,
            download_dir: str,
            progress_callback: Callable[[DownloadItem, float], None],
            completion_callback: Callable[[bool, Optional[str]],  None]
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


    def has_active_downloads(self) -> bool:
        """Check if there are any active downloads."""
        with self._lock:
            return any(item.status == "Downloading" for item in self.items)

    def cleanup(self) -> None:
        """Clean up resources and stop any active downloads."""
        with self._lock:
            # Mark any downloading items as failed
            for item in self.items:
                if item.status == "Downloading":
                    item.status = "Failed"

            # Clear the items list
            self.items.clear()

            # Reset internal state
            self.active_downloads = 0

            # Reset downloaders
            self.youtube_downloader = YouTubeDownloader()
            self.twitter_downloader = TwitterDownloader()
            self.pinterest_downloader = PinterestDownloader()

            # Reset options
            self.youtube_options = {
                'quality': '720p',
                'playlist': None,
                'audio_only': None
            }

            logger.info("Download manager cleaned up")

