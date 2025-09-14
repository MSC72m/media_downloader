import threading
import logging
from typing import List, Callable, Optional, Dict, Any
from urllib.parse import urlparse
import os

from src.models import DownloadItem, DownloadOptions, VideoQuality, DownloadStatus, ServiceType
from src.downloaders.youtube import YouTubeDownloader
from src.downloaders.twitter import TwitterDownloader
from src.downloaders.instagram import InstagramDownloader
from src.downloaders.pinterest import PinterestDownloader
from src.downloaders.base import BaseDownloader

logger = logging.getLogger(__name__)

class DownloadManager:
    """Manages download operations and state."""

    def __init__(self):
        self._items: List[DownloadItem] = []
        self._active_downloads = 0
        self._options = DownloadOptions()
        self._lock = threading.Lock()
        self._auth_manager = None

        # Initialize downloaders
        self._youtube_downloader = YouTubeDownloader()
        self._twitter_downloader = TwitterDownloader()
        self._instagram_downloader = InstagramDownloader()
        self._pinterest_downloader = PinterestDownloader()

        # Flat domain to service mapping for O(1) lookup - consistent with main.py
        self._domain_to_service = {
            'youtube.com': ServiceType.YOUTUBE,
            'youtu.be': ServiceType.YOUTUBE,
            'twitter.com': ServiceType.TWITTER,
            'x.com': ServiceType.TWITTER,
            'instagram.com': ServiceType.INSTAGRAM,
            'pinterest.com': ServiceType.PINTEREST,
            'pin.it': ServiceType.PINTEREST
        }

    @property
    def downloaders_service_dict(self) -> Dict[ServiceType, BaseDownloader]:
        """Get a dictionary of downloaders by service type."""
        return {
            ServiceType.YOUTUBE: self._youtube_downloader,
            ServiceType.TWITTER: self._twitter_downloader,
            ServiceType.INSTAGRAM: self._instagram_downloader,
            ServiceType.PINTEREST: self._pinterest_downloader
        }
    
    @property
    def items(self) -> List[DownloadItem]:
        """Get a copy of the download items."""
        with self._lock:
            return self._items.copy()
    
    @property
    def options(self) -> DownloadOptions:
        """Get the current download options."""
        return self._options
    
    @property
    def auth_manager(self) -> Any:
        """Get the authentication manager."""
        return self._auth_manager
    
    @auth_manager.setter
    def auth_manager(self, value: Any) -> None:
        """Set the authentication manager."""
        self._auth_manager = value
    
    @property
    def quality(self) -> VideoQuality:
        """Get the current video quality setting."""
        return self._options.quality
    
    @quality.setter
    def quality(self, quality: str) -> None:
        """Set video quality."""
        try:
            self._options.quality = VideoQuality(quality)
            self._update_youtube_downloader()
        except ValueError:
            logger.error(f"Invalid video quality: {quality}")
            self._options.quality = VideoQuality.HD
    
    def _update_youtube_downloader(self) -> None:
        """Update the YouTube downloader with current options."""
        self._youtube_downloader = YouTubeDownloader(
            quality=self._options.quality.value,
            download_playlist=self._options.playlist,
            audio_only=self._options.audio_only
        )
    
    def set_option(self, option: str, value: bool) -> None:
        """Set download option."""
        if option == 'playlist':
            self._options.playlist = value
        elif option == 'audio_only':
            self._options.audio_only = value
        
        # Update downloader with new options
        self._update_youtube_downloader()

    @property
    def save_directory(self) -> str:
        """Get the current save directory."""
        return self._options.save_directory
    
    @save_directory.setter
    def save_directory(self, directory: str) -> None:
        """Set save directory."""
        self._options.save_directory = directory
        os.makedirs(directory, exist_ok=True)

    def add_item(self, item: DownloadItem) -> None:
        """Add a download item to the queue."""
        with self._lock:
            self._items.append(item)

    def remove_items(self, indices: List[int]) -> None:
        """Remove items at the specified indices."""
        with self._lock:
            for index in sorted(indices, reverse=True):
                if 0 <= index < len(self._items):
                    self._items.pop(index)

    def clear_items(self) -> None:
        """Clear all download items."""
        with self._lock:
            self._items.clear()

    def has_items(self) -> bool:
        """Check if there are any items in the download queue."""
        with self._lock:
            return len(self._items) > 0

    def _get_downloader_for_url(self, url: str) -> Optional[BaseDownloader]:
        """Get the appropriate downloader for a URL."""
        domain = urlparse(url).netloc.lower()
        logger.debug(f"Checking URL: {url}, domain: {domain}")

        # Check if domain is in our mapping
        service_type = self._domain_to_service.get(domain)
        if service_type:
            logger.debug(f"Found direct match: {domain} -> {service_type}")
            return self.downloaders_service_dict.get(service_type)

        # Fallback: check if any domain pattern matches
        for domain_pattern, service_type in self._domain_to_service.items():
            if domain_pattern in domain:
                logger.debug(f"Found pattern match: {domain_pattern} in {domain} -> {service_type}")
                return self.downloaders_service_dict.get(service_type)

        logger.debug(f"No downloader found for domain: {domain}")
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
                item.update_progress(progress, speed)
                if progress_callback:
                    progress_callback(progress)

            return downloader.download(item.url, save_path, progress_wrapper)

        except Exception as e:
            logger.error(f"Error downloading {item.name}: {str(e)}")
            item.mark_failed(str(e))
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
                    items_to_download = [item for item in self._items if item.status == DownloadStatus.PENDING]

                for item in items_to_download:
                    item.status = DownloadStatus.DOWNLOADING

                    def item_progress(progress: float):
                        progress_callback(item, progress)

                    success = self._download_item(
                        item,
                        download_dir,
                        item_progress
                    )
                    
                    if not success and item.status != DownloadStatus.FAILED:
                        item.mark_failed("Download failed")

                completion_callback(True)
            except Exception as e:
                logger.error(f"Download worker error: {str(e)}")
                completion_callback(False, str(e))

        threading.Thread(target=download_worker, daemon=True).start()

    def has_active_downloads(self) -> bool:
        """Check if there are any active downloads."""
        with self._lock:
            return any(item.status == DownloadStatus.DOWNLOADING for item in self._items)

    def cleanup(self) -> None:
        """Clean up resources and stop any active downloads."""
        with self._lock:
            # Mark any downloading items as failed
            for item in self._items:
                if item.status == DownloadStatus.DOWNLOADING:
                    item.mark_failed("Cancelled by user")

            # Clear the items list
            self._items.clear()

            # Reset internal state
            self._active_downloads = 0
            
            # Reset options
            self._options = DownloadOptions()

            # Reset downloaders
            self._youtube_downloader = YouTubeDownloader()
            self._twitter_downloader = TwitterDownloader()
            self._pinterest_downloader = PinterestDownloader()

            logger.info("Download manager cleaned up")

