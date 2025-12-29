import os
from collections.abc import Callable
from typing import Any

import requests

from src.core.config import AppConfig, get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from src.services.network.downloader import download_file

from ...utils.logger import get_logger

logger = get_logger(__name__)


class RadioJavanDownloader(BaseDownloader):
    """Radio Javan downloader using API and URL validation."""

    CDN_HOSTS = [
        "rj1.media",
        "rj2.media",
        "rj3.media",
        "rjmedia.app",
        "rj.app",
    ]

    MP3_PATHS = [
        "/media/mp3/{media_name}",
        "/mp3/{media_name}",
        "/mp3s/{media_name}",
    ]

    MP4_PATHS = [
        "/media/mp4/{media_name}",
        "/mp4/{media_name}",
        "/mp4s/{media_name}",
    ]

    MIN_FILE_SIZE = 1024

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config=None,
    ):
        if config is None:
            config = get_config()
        super().__init__(error_handler, file_service, config)
        self.default_timeout = config.radiojavan.default_timeout
        self.max_retries = config.radiojavan.max_retries

    def _validate_download_inputs(self, url: str, save_path: str) -> bool:
        """Validate download inputs.

        Args:
            url: Radio Javan URL
            save_path: Path to save file

        Returns:
            True if valid, False otherwise
        """
        if not url:
            error_msg = "No URL provided"
            logger.error(f"[RADIOJAVAN_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Radio Javan", "download", error_msg, "")
            return False

        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            error_msg = f"Save directory does not exist: {save_dir}"
            logger.error(f"[RADIOJAVAN_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Radio Javan", "download", error_msg, url)
            return False

        return True

    def _extract_media_name(self, url: str) -> str | None:
        """Extract media name from Radio Javan URL.

        Args:
            url: Radio Javan URL

        Returns:
            Media name or None
        """
        import re

        patterns = [
            r"/mp3/([\w-]+)",
            r"/mp4/([\w-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _construct_download_url(self, url: str) -> str | None:
        """Construct direct download URL from Radio Javan URL.

        Args:
            url: Radio Javan URL

        Returns:
            Direct download URL or None if construction failed
        """
        media_name = self._extract_media_name(url)
        if not media_name:
            return None

        is_mp3 = "/mp3/" in url.lower()
        is_mp4 = "/mp4/" in url.lower()

        paths = self.MP3_PATHS if is_mp3 else self.MP4_PATHS

        for host in self.CDN_HOSTS:
            for path in paths:
                download_url = f"https://{host}{path.format(media_name=media_name)}"
                if self._validate_url(download_url):
                    logger.debug(f"[RADIOJAVAN_DOWNLOADER] Valid URL found: {download_url}")
                    return download_url

        logger.warning(f"[RADIOJAVAN_DOWNLOADER] Could not construct valid URL for: {url}")
        return None

    def _validate_url(self, url: str) -> bool:
        """Validate if URL returns a valid file.

        Args:
            url: Download URL to validate

        Returns:
            True if valid file, False otherwise
        """
        try:
            logger.debug(f"[RADIOJAVAN_DOWNLOADER] Validating URL: {url}")
            response = requests.head(url, timeout=self.default_timeout, allow_redirects=True)
            response.raise_for_status()

            content_length = response.headers.get("content-length", "0")
            file_size = int(content_length) if content_length.isdigit() else 0

            if file_size < self.MIN_FILE_SIZE:
                logger.warning(f"[RADIOJAVAN_DOWNLOADER] File too small: {file_size} bytes")
                return False

            logger.debug(f"[RADIOJAVAN_DOWNLOADER] URL valid: {file_size} bytes")
            return True

        except requests.RequestException as e:
            logger.debug(f"[RADIOJAVAN_DOWNLOADER] URL validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"[RADIOJAVAN_DOWNLOADER] Error validating URL: {e}")
            return False

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] = None,
    ) -> bool:
        """Download a Radio Javan media file.

        Args:
            url: Radio Javan URL
            save_path: Path to save file (without extension)
            progress_callback: Optional callback for progress updates (progress%, speed)

        Returns:
            bool: True if download successful, False otherwise
        """
        if not self._validate_download_inputs(url, save_path):
            return False

        logger.info(f"[RADIOJAVAN_DOWNLOADER] Starting download: {url}")
        logger.info(f"[RADIOJAVAN_DOWNLOADER] Save path: {save_path}")

        download_url = self._construct_download_url(url)
        if not download_url:
            error_msg = "Could not construct valid download URL"
            logger.error(f"[RADIOJAVAN_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("Radio Javan", "download", error_msg, url)
            return False

        return download_file(
            url=download_url,
            save_path=save_path,
            progress_callback=progress_callback,
            config=self.config,
        )
