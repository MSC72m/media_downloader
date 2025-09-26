"""Twitter downloader service implementation."""

import requests
import re
import logging
from typing import Optional, List, Callable
import os

from ...downloaders.base import BaseDownloader
from ...utils.common import download_file, sanitize_filename

logger = logging.getLogger(__name__)


class TwitterDownloader(BaseDownloader):
    """Twitter downloader service."""

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
            tweet_ids = self._extract_tweet_ids(url)
            if not tweet_ids:
                logger.error("No tweet IDs found")
                return False

            success = False
            for i, tweet_id in enumerate(tweet_ids):
                media = self._scrape_media(tweet_id)
                if media:
                    save_name = f"{save_path}_{i}" if len(tweet_ids) > 1 else save_path
                    if self._download_media(media, save_name, progress_callback):
                        success = True

            return success

        except Exception as e:
            logger.error(f"Error downloading from Twitter: {str(e)}")
            return False

    @staticmethod
    def _extract_tweet_ids(text: str) -> Optional[List[str]]:
        """Extract tweet IDs from a Twitter URL."""
        tweet_ids = re.findall(
            r"(?:twitter|x)\.com/.{1,15}/(?:web|status(?:es)?)/([0-9]{1,20})", text)
        return list(dict.fromkeys(tweet_ids)) if tweet_ids else None

    @staticmethod
    def _scrape_media(tweet_id: int) -> List[dict]:
        """Scrape media from a tweet using VX Twitter API."""
        try:
            response = requests.get(
                f'https://api.vxtwitter.com/Twitter/status/{tweet_id}',
                verify=False,
                timeout=10
            )
            response.raise_for_status()
            return response.json().get('media_extended', [])
        except Exception as e:
            logger.error(f"Error scraping media: {str(e)}")
            return []

    @staticmethod
    def _download_media(
            media: List[dict],
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """Download media files from tweet media data."""
        for item in media:
            try:
                url = item['url']
                ext = '.mp4' if item['type'] == 'video' else '.jpg'
                filename = sanitize_filename(f'{os.path.basename(save_path)}{ext}')
                full_path = os.path.join(os.path.dirname(save_path), filename)

                return download_file(url, full_path, progress_callback)
            except Exception as e:
                logger.error(f"Error downloading media: {str(e)}")
                continue
        return False