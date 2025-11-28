"""Twitter downloader service implementation."""

import os
import re
from typing import Callable, List, Optional

import requests

from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from ...core.enums import ServiceType
from ...utils.logger import get_logger
from ..file.service import FileService
from ..network.checker import check_site_connection

logger = get_logger(__name__)


class TwitterDownloader(BaseDownloader):
    """Twitter downloader service."""

    def __init__(self, error_handler: Optional[IErrorNotifier] = None, file_service: Optional[IFileService] = None, config=None):
        """Initialize Twitter downloader.

        Args:
            error_handler: Optional error handler for user notifications
            file_service: Optional file service for file operations
            config: AppConfig instance (defaults to get_config() if None)
        """
        from src.core.config import get_config as _get_config
        if config is None:
            config = _get_config()
        super().__init__(error_handler, file_service, config)
        if not self.file_service:
            self.file_service = FileService()

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Download media from Twitter URLs.

        Args:
            url: Twitter URL to download from
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        try:
            connected, error_msg = check_site_connection(ServiceType.TWITTER)
            if not connected:
                logger.error(f"Cannot download from Twitter: {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure("Twitter", "download", error_msg or "Connection failed", url)
                return False

            tweet_ids = self._extract_tweet_ids(url)
            if not tweet_ids:
                error_msg = "No tweet IDs found in URL"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure("Twitter", "download", error_msg, url)
                return False

            success = False
            for i, tweet_id in enumerate(tweet_ids):
                media = self._scrape_media(tweet_id)
                if media:
                    save_name = f"{save_path}_{i}" if len(tweet_ids) > 1 else save_path
                    if self._download_media(media, save_name, progress_callback):
                        success = True

            if not success:
                error_msg = "Failed to download media from tweet"
                if self.error_handler:
                    self.error_handler.handle_service_failure("Twitter", "download", error_msg, url)

            return success

        except Exception as e:
            logger.error(f"Error downloading from Twitter: {str(e)}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Twitter download", "Twitter")
            return False

    @staticmethod
    def _extract_tweet_ids(text: str) -> Optional[List[str]]:
        """Extract tweet IDs from a Twitter URL."""
        tweet_ids = re.findall(
            r"(?:twitter|x)\.com/.{1,15}/(?:web|status(?:es)?)/([0-9]{1,20})", text)
        return list(dict.fromkeys(tweet_ids)) if tweet_ids else None

    def _scrape_media(self, tweet_id: int) -> List[dict]:
        """Scrape media from a tweet using VX Twitter API."""
        try:
            response = requests.get(
                f'https://api.vxtwitter.com/Twitter/status/{tweet_id}',
                verify=True,
                timeout=self.config.network.twitter_api_timeout
            )
            response.raise_for_status()
            return response.json().get('media_extended', [])
        except Exception as e:
            logger.error(f"Error scraping media: {str(e)}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, f"Scraping tweet {tweet_id}", "Twitter")
            return []

    def _download_media(
            self,
            media: List[dict],
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """Download media files from tweet media data."""
        success = False

        for i, item in enumerate(media):
            try:
                url = item['url']
                ext = '.mp4' if item['type'] == 'video' else '.jpg'
                
                if len(media) > 1:
                    filename = self.file_service.sanitize_filename(
                        f'{os.path.basename(save_path)}_{i}{ext}'
                    )
                else:
                    filename = self.file_service.sanitize_filename(
                        f'{os.path.basename(save_path)}{ext}'
                    )
                
                full_path = os.path.join(os.path.dirname(save_path), filename)

                file_service = FileService()
                result = file_service.download_file(url, full_path, progress_callback)
                if result.success:
                    success = True
            except Exception as e:
                logger.error(f"Error downloading media item {i}: {str(e)}", exc_info=True)
                if self.error_handler:
                    self.error_handler.handle_exception(e, f"Downloading media item {i}", "Twitter")
                continue
        
        return success
