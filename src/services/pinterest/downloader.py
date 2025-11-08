"""Pinterest downloader service implementation."""

from src.utils.logger import get_logger
import os
from typing import Optional, Callable
import requests
import re
from bs4 import BeautifulSoup

from ...core import BaseDownloader
from ...core.enums import ServiceType
from ..file.service import FileService
from ..file.sanitizer import FilenameSanitizer
from ..network.checker import check_site_connection

logger = get_logger(__name__)


class PinterestDownloader(BaseDownloader):
    """Pinterest downloader service."""

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Download media from Pinterest URLs.

        Args:
            url: Pinterest URL to download from
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Check connectivity to Pinterest
            connected, error_msg = check_site_connection(ServiceType.PINTEREST)
            if not connected:
                logger.error(f"Cannot download from Pinterest: {error_msg}")
                return False

            # Get media URL from Pinterest
            media_url = self._get_media_url(url)
            if not media_url:
                logger.error("Could not retrieve media URL from Pinterest")
                return False

            # Download the media
            save_dir = self._get_save_directory(save_path)
            self._ensure_directory_exists(save_path)
            
            sanitizer = FilenameSanitizer()
            filename = sanitizer.sanitize_filename(os.path.basename(save_path))
            
            # Detect file extension from URL or use default
            ext = self._get_extension_from_url(media_url) or '.jpg'
            full_path = os.path.join(save_dir, filename + ext)

            file_service = FileService()
            result = file_service.download_file(media_url, full_path, progress_callback)
            return result.success

        except Exception as e:
            logger.error(f"Error downloading from Pinterest: {str(e)}")
            return False

    @staticmethod
    def _get_extension_from_url(url: str) -> Optional[str]:
        """Extract file extension from URL."""
        try:
            # Get the path from URL and extract extension
            match = re.search(r'\.([a-zA-Z0-9]+)(?:\?|$)', url)
            if match:
                ext = match.group(1).lower()
                # Common image/video extensions
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm']:
                    return f'.{ext}'
            return None
        except Exception:
            return None

    @staticmethod
    def _get_media_url(url: str) -> Optional[str]:
        """Get media URL from Pinterest pin URL."""
        try:
            # Method 1: Try oembed endpoint
            oembed_url = f"https://www.pinterest.com/oembed/?url={url}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            response = requests.get(oembed_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Try to get the image URL from oembed response
                if 'url' in data:
                    return data['url']
                if 'thumbnail_url' in data:
                    return data['thumbnail_url']
            
            # Method 2: Scrape the page directly
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Try to find og:image meta tag (highest quality)
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    return og_image['content']
                
                # Try to find pinterest:image meta tag
                pin_image = soup.find('meta', attrs={'name': 'pinterest:image'})
                if pin_image and pin_image.get('content'):
                    return pin_image['content']
                
                # Try to find image in structured data
                script_tags = soup.find_all('script', type='application/ld+json')
                for script in script_tags:
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict) and 'image' in data:
                            img = data['image']
                            if isinstance(img, str):
                                return img
                            elif isinstance(img, dict) and 'url' in img:
                                return img['url']
                    except Exception:
                        continue

            return None
            
        except Exception as e:
            logger.error(f"Error getting Pinterest media URL: {e}")
            return None
