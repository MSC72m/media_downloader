"""Pinterest downloader service implementation."""

import json
import os
import re
from typing import Callable, Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.core.config import get_config, AppConfig
from src.core.enums import ServiceType
from src.interfaces.service_interfaces import BaseDownloader, IErrorHandler
from ...utils.logger import get_logger
from ..file.sanitizer import FilenameSanitizer
from ..file.service import FileService
from ..network.checker import check_site_connection

logger = get_logger(__name__)


class PinterestDownloader(BaseDownloader):
    """Pinterest downloader service."""

    def __init__(self, error_handler: Optional[IErrorHandler] = None, config=None):
        """Initialize Pinterest downloader.

        Args:
            error_handler: Optional error handler for user notifications
            config: AppConfig instance (defaults to get_config() if None)
        """
        super().__init__(config)
        self.error_handler = error_handler

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None,
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
            connected, error_msg = check_site_connection(ServiceType.PINTEREST)
            if not connected:
                logger.error(f"Cannot download from Pinterest: {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure("Pinterest", "download", error_msg or "Connection failed", url)
                return False

            media_url = self._get_media_url(url)
            if not media_url:
                error_msg = "Could not retrieve media URL from Pinterest"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure("Pinterest", "download", error_msg, url)
                return False

            save_dir = self._get_save_directory(save_path)
            self._ensure_directory_exists(save_path)

            sanitizer = FilenameSanitizer()
            filename = sanitizer.sanitize_filename(os.path.basename(save_path))

            ext = self._get_extension_from_url(media_url) or ".jpg"
            full_path = os.path.join(save_dir, filename + ext)

            file_service = FileService()
            result = file_service.download_file(media_url, full_path, progress_callback)
            
            if not result.success:
                error_msg = "Failed to download media file"
                if self.error_handler:
                    self.error_handler.handle_service_failure("Pinterest", "download", error_msg, url)
            
            return result.success

        except Exception as e:
            logger.error(f"Error downloading from Pinterest: {str(e)}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Pinterest download", "Pinterest")
            return False

    @staticmethod
    def _get_extension_from_url(url: str) -> Optional[str]:
        """Extract file extension from URL."""
        try:
            # Get the path from URL and extract extension
            match = re.search(r"\.([a-zA-Z0-9]+)(?:\?|$)", url)
            if match:
                ext = match.group(1).lower()
                # Common image/video extensions
                if ext in ["jpg", "jpeg", "png", "gif", "webp", "mp4", "webm"]:
                    return f".{ext}"
            return None
        except Exception:
            return None

    def _get_media_url(self, url: str) -> Optional[str]:
        """Get media URL from Pinterest pin URL."""
        try:
            # Method 1: Try oembed endpoint
            oembed_url = f"https://www.pinterest.com/oembed/?url={url}"
            headers = {
                "User-Agent": self.config.network.user_agent
            }

            response = requests.get(oembed_url, headers=headers, timeout=self.config.pinterest.oembed_timeout)
            if response.status_code == 200:
                data = response.json()
                # Try to get the image URL from oembed response
                if "url" in data:
                    return data["url"]
                if "thumbnail_url" in data:
                    return data["thumbnail_url"]

            # Method 2: Scrape the page directly
            response = requests.get(url, headers=headers, timeout=self.config.pinterest.default_timeout)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Try to find og:image meta tag (highest quality)
                og_image = soup.find("meta", property="og:image")
                if isinstance(og_image, Tag):
                    content = og_image.get("content")
                    if content and isinstance(content, str):
                        return content

                # Try to find pinterest:image meta tag
                pin_image = soup.find("meta", attrs={"name": "pinterest:image"})
                if isinstance(pin_image, Tag):
                    content = pin_image.get("content")
                    if content and isinstance(content, str):
                        return content

                # Try to find image in structured data
                script_tags = soup.find_all("script", type="application/ld+json")
                for script in script_tags:
                    try:
                        if isinstance(script, Tag) and script.string:
                            data = json.loads(script.string)
                            if not isinstance(data, dict) and "image" in data:
                                logger.warning(f"Invalid structured data: {data}")
                                continue

                            img = data["image"]
                            if isinstance(img, str):
                                return img

                            if (
                                isinstance(img, dict)
                                and "url" in img
                                and isinstance(img["url"], str)
                            ):
                                return img["url"]
                                
                    except Exception:
                        continue
            return None

        except Exception as e:
            logger.error(f"Error getting Pinterest media URL: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Getting Pinterest media URL", "Pinterest")
            return None
