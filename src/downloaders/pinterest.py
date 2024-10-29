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
            response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            image_tag = soup.find('meta', property='og:image')
            image_url = image_tag['content'] if image_tag else None

            if image_url:
                sanitized_filename = sanitize_filename(f'{os.path.basename(save_path)}.jpg')
                full_save_path = os.path.join(os.path.dirname(save_path), sanitized_filename)
                return download_file(image_url, full_save_path, progress_callback)
            else:
                logger.error("Image URL not found.")
                return False

        except Exception as e:
            logger.error(f"Error downloading Pinterest image: {str(e)}")
            return False