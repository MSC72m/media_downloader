"""Pinterest downloader service implementation."""

from src.utils.logger import get_logger
import os
from typing import Optional, Callable
import requests

from ...core import BaseDownloader
from ..file.service import FileService
from ..file.sanitizer import FilenameSanitizer

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
            # Extract pin ID from URL
            pin_id = self._extract_pin_id(url)
            if not pin_id:
                logger.error("No Pinterest pin ID found")
                return False

            # Get media URL from Pinterest API
            media_url = self._get_media_url(pin_id)
            if not media_url:
                logger.error("Could not retrieve media URL")
                return False

            # Download the media
            save_dir = os.path.dirname(save_path)
            sanitizer = FilenameSanitizer()
            filename = sanitizer.sanitize_filename(os.path.basename(save_path))
            full_path = os.path.join(save_dir, filename + '.jpg')  # Pinterest images are typically JPG

            file_service = FileService()
            result = file_service.download_file(media_url, full_path, progress_callback)
            return result.success

        except Exception as e:
            logger.error(f"Error downloading from Pinterest: {str(e)}")
            return False

    @staticmethod
    def _extract_pin_id(url: str) -> Optional[str]:
        """Extract Pinterest pin ID from URL."""
        try:
            import re
            # Match Pinterest URL patterns
            patterns = [
                r'pinterest\.com/pin/(\d+)',
                r'pinterest\.com/pin/([^/]+)',
                r'pin\.it/([^/]+)'
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)

            return None
        except Exception:
            return None

    @staticmethod
    def _get_media_url(pin_id: str) -> Optional[str]:
        """Get media URL from Pinterest pin ID."""
        try:
            # Use Pinterest's oEmbed API or other public endpoints
            # Note: This is a simplified implementation
            api_url = f"https://api.pinterest.com/v1/pins/{pin_id}/"

            # In a real implementation, you would need proper API credentials
            # For now, we'll try to get the image URL directly
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                # Parse response to extract image URL
                # This is a simplified version - real implementation would parse JSON
                return response.json().get('data', {}).get('image', {}).get('original', {}).get('url')

            return None
        except Exception as e:
            logger.error(f"Error getting Pinterest media URL: {e}")
            return None