import requests
import logging
import os
from typing import Optional, Callable
from bs4 import BeautifulSoup

from src.utils.common import download_file, sanitize_filename
from .base import BaseDownloader

logger = logging.getLogger(__name__)


class PinterestDownloader(BaseDownloader):
    def download(
            self,
            url: str,
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        try:
            # Pinterest requires proper headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            # Get the Pinterest page
            page_response = requests.get(url, headers=headers, timeout=10)
            page_response.raise_for_status()

            soup = BeautifulSoup(page_response.text, 'html.parser')

            # Try different meta tags to find the image
            image_url = None
            for meta in soup.find_all('meta'):
                if meta.get('property') in ['og:image', 'og:image:url']:
                    image_url = meta.get('content')
                    if image_url:
                        # Make sure we get the highest quality version
                        image_url = image_url.replace('236x', 'originals')
                        break

            if not image_url:
                logger.error("Could not find image URL in Pinterest page")
                return False

            # Create proper filename
            sanitized_filename = sanitize_filename(f'{os.path.basename(save_path)}.jpg')
            full_save_path = os.path.join(os.path.dirname(save_path), sanitized_filename)

            # Wrap progress callback to handle potential missing speed parameter
            def progress_wrapper(progress: float, speed: float = 0):
                if progress_callback:
                    try:
                        progress_callback(progress, speed)
                    except TypeError:
                        progress_callback(progress, 0)  # Fallback if callback doesn't accept speed

            # Download the image with progress tracking
            success = download_file(image_url, full_save_path, progress_wrapper)

            if success:
                logger.info(f"Successfully downloaded Pinterest image to {full_save_path}")
            else:
                logger.error("Failed to download Pinterest image")

            return success

        except Exception as e:
            logger.error(f"Error downloading Pinterest image: {str(e)}")
            return False