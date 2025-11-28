"""Pinterest downloader service implementation."""

import json
import os
import re
from collections.abc import Callable

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

from src.core.config import get_config
from src.core.enums import ServiceType
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService

from ...utils.logger import get_logger
from ..file.service import FileService
from ..network.checker import check_site_connection

logger = get_logger(__name__)


class PinterestDownloader(BaseDownloader):
    """Pinterest downloader service."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config=None,
    ):
        """Initialize Pinterest downloader.

        Args:
            error_handler: Optional error handler for user notifications
            file_service: Optional file service for file operations
            config: AppConfig instance (defaults to get_config() if None)
        """
        if config is None:
            config = get_config()
        super().__init__(error_handler, file_service, config)
        if not self.file_service:
            self.file_service = FileService()

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
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
                    self.error_handler.handle_service_failure(
                        "Pinterest", "download", error_msg or "Connection failed", url
                    )
                return False

            media_url = self._get_media_url(url)
            if not media_url:
                error_msg = "Could not retrieve media URL from Pinterest"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Pinterest", "download", error_msg, url
                    )
                return False

            save_dir = os.path.dirname(save_path) if os.path.dirname(save_path) else "."
            file_service = FileService()
            self.file_service.ensure_directory(save_dir)

            filename = self.file_service.sanitize_filename(os.path.basename(save_path))

            ext = self._get_extension_from_url(media_url) or ".jpg"
            full_path = os.path.join(save_dir, filename + ext)
            result = file_service.download_file(media_url, full_path, progress_callback)

            if not result.success:
                error_msg = "Failed to download media file"
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Pinterest", "download", error_msg, url
                    )

            return result.success

        except Exception as e:
            logger.error(f"Error downloading from Pinterest: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Pinterest download", "Pinterest")
            return False

    @staticmethod
    def _get_extension_from_url(url: str) -> str | None:
        """Extract file extension from URL."""
        try:
            # Get the path from URL and extract extension
            match = re.search(r"\.([a-zA-Z0-9]+)(?:\?|$)", url)
            if match:
                ext = match.group(1).lower()
                # Common image/video extensions
                # Use set for O(1) membership check instead of O(n) list check
                valid_extensions = {"jpg", "jpeg", "png", "gif", "webp", "mp4", "webm"}
                if ext in valid_extensions:
                    return f".{ext}"
            return None
        except Exception:
            return None

    def _try_oembed(self, url: str) -> str | None:
        """Try to get media URL from oembed endpoint.

        Args:
            url: Pinterest pin URL

        Returns:
            Media URL if found, None otherwise
        """
        oembed_url = f"https://www.pinterest.com/oembed/?url={url}"
        headers = {"User-Agent": self.config.network.user_agent}

        try:
            response = requests.get(
                oembed_url,
                headers=headers,
                timeout=self.config.pinterest.oembed_timeout,
            )
            if response.status_code == 200:
                data = response.json()
                if "url" in data:
                    return data["url"]
                if "thumbnail_url" in data:
                    return data["thumbnail_url"]
        except Exception:
            pass
        return None

    def _extract_from_meta_tags(self, soup: BeautifulSoup) -> str | None:
        """Extract image URL from meta tags.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Image URL if found, None otherwise
        """
        og_image = soup.find("meta", property="og:image")
        if isinstance(og_image, Tag):
            content = og_image.get("content")
            if content and isinstance(content, str):
                return content

        pin_image = soup.find("meta", attrs={"name": "pinterest:image"})
        if isinstance(pin_image, Tag):
            content = pin_image.get("content")
            if content and isinstance(content, str):
                return content
        return None

    def _extract_from_structured_data(self, soup: BeautifulSoup) -> str | None:
        """Extract image URL from structured data.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Image URL if found, None otherwise
        """
        script_tags = soup.find_all("script", type="application/ld+json")
        for script in script_tags:
            try:
                if not isinstance(script, Tag) or not script.string:
                    continue

                data = json.loads(script.string)
                if not isinstance(data, dict) or "image" not in data:
                    continue

                img = data["image"]
                if isinstance(img, str):
                    return img

                if isinstance(img, dict) and "url" in img and isinstance(img["url"], str):
                    return img["url"]
            except Exception as e:
                logger.debug(f"Error processing image: {e}")
                continue
        return None

    def _get_media_url(self, url: str) -> str | None:
        """Get media URL from Pinterest pin URL."""
        try:
            oembed_result = self._try_oembed(url)
            if oembed_result:
                return oembed_result

            headers = {"User-Agent": self.config.network.user_agent}
            response = requests.get(
                url, headers=headers, timeout=self.config.pinterest.default_timeout
            )
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            meta_result = self._extract_from_meta_tags(soup)
            if meta_result:
                return meta_result

            return self._extract_from_structured_data(soup)

        except Exception as e:
            logger.error(f"Error getting Pinterest media URL: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Getting Pinterest media URL", "Pinterest")
            return None
