import os
import re
from collections.abc import Callable
from typing import ClassVar

import requests

from src.core.config import get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from src.services.network.downloader import download_file

from ...utils.logger import get_logger

logger = get_logger(__name__)


class RadioJavanDownloader(BaseDownloader):
    """Radio Javan downloader using API and URL validation."""

    CDN_HOSTS: ClassVar[list[str]] = [
        "https://rj1.media",
        "https://rj2.media",
        "https://rj3.media",
        "https://rjmedia.app",
        "https://rj.app",
    ]

    MP3_PATHS: ClassVar[list[str]] = [
        "/media/mp3/mp3-320/{media_name}.mp3",
        "/media/mp3/mp3-256/{media_name}.mp3",
        "/media/mp3/{media_name}.mp3",
        "/media/mp3/{media_name}",
        "/mp3/{media_name}",
        "/mp3s/{media_name}",
    ]

    MP4_PATHS: ClassVar[list[str]] = [
        "/media/music_video/hd/{media_name}.mp4",
        "/media/music_video/hq/{media_name}.mp4",
        "/media/music_video/lq/{media_name}.mp4",
        "/media/mp4/{media_name}.mp4",
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
        self._api_base = str(config.radiojavan.api_base_url).rstrip("/")
        self._headers = {"User-Agent": self.config.network.user_agent}

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
        from urllib.parse import unquote

        patterns = [
            r"/mp3s/mp3/([\w%-]+)",
            r"/videos/video/([\w%-]+)",
            r"/mp3/([\w%-]+)",
            r"/mp4/([\w%-]+)",
            r"/song/([\w%-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return unquote(match.group(1))
        return None

    @staticmethod
    def _detect_media_type(url: str) -> str | None:
        """Detect whether URL points to mp3 or mp4 content."""
        lowered = url.lower()
        match lowered:
            case value if any(token in value for token in ("/mp3s/mp3/", "/mp3/", "/song/")):
                return "mp3"
            case value if any(token in value for token in ("/videos/video/", "/mp4/")):
                return "mp4"
            case _:
                return None

    @staticmethod
    def _normalize_host(host: str) -> str:
        """Normalize host string into full https://base form."""
        cleaned = host.strip().rstrip("/")
        if cleaned.startswith(("http://", "https://")):
            return cleaned
        return f"https://{cleaned}"

    def _candidate_hosts(self, media_name: str, media_type: str) -> list[str]:
        """Get candidate hosts using Radio Javan API first, then static fallbacks."""
        hosts: list[str] = []
        endpoint_map = {
            "mp3": "mp3s/mp3_host",
            "mp4": "videos/video_host",
        }
        endpoint = endpoint_map.get(media_type)

        if endpoint:
            try:
                response = requests.post(
                    f"{self._api_base}/{endpoint}",
                    params={"id": media_name},
                    headers=self._headers,
                    timeout=self.default_timeout,
                )
                response.raise_for_status()
                payload = response.json()
                host = payload.get("host")
                if isinstance(host, str) and host.strip():
                    hosts.append(self._normalize_host(host))
            except Exception as e:
                logger.warning(f"[RADIOJAVAN_DOWNLOADER] Host API lookup failed: {e}")

        configured_hosts = [self._normalize_host(h) for h in self.config.radiojavan.cdn_hosts]
        fallback_hosts = [self._normalize_host(h) for h in self.CDN_HOSTS]
        hosts.extend(configured_hosts)
        hosts.extend(fallback_hosts)

        unique_hosts: list[str] = []
        seen: set[str] = set()
        for host in hosts:
            if host in seen:
                continue
            seen.add(host)
            unique_hosts.append(host)
        return unique_hosts

    def _candidate_paths(self, media_type: str) -> list[str]:
        """Get URL path candidates for media type."""
        return self.MP3_PATHS if media_type == "mp3" else self.MP4_PATHS

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

        media_type = self._detect_media_type(url)
        if not media_type:
            logger.warning(f"[RADIOJAVAN_DOWNLOADER] Could not detect media type: {url}")
            return None

        hosts = self._candidate_hosts(media_name, media_type)
        paths = self._candidate_paths(media_type)

        first_candidate: str | None = None
        for host in hosts:
            for path in paths:
                download_url = f"{host}{path.format(media_name=media_name)}"
                if first_candidate is None:
                    first_candidate = download_url
                if self._validate_url(download_url):
                    logger.debug(f"[RADIOJAVAN_DOWNLOADER] Valid URL found: {download_url}")
                    return download_url

        if first_candidate:
            logger.warning(
                "[RADIOJAVAN_DOWNLOADER] No candidate URL validated; returning best-effort URL: "
                f"{first_candidate}"
            )
            return first_candidate

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
            response = requests.head(
                url,
                timeout=self.default_timeout,
                allow_redirects=True,
                headers=self._headers,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if not any(token in content_type for token in ("audio", "video", "octet-stream")):
                return False

            content_length = response.headers.get("content-length", "0")
            file_size = int(content_length) if content_length.isdigit() else 0
            if file_size and file_size < self.MIN_FILE_SIZE:
                logger.warning(f"[RADIOJAVAN_DOWNLOADER] File too small: {file_size} bytes")
                return False

            logger.debug(f"[RADIOJAVAN_DOWNLOADER] URL valid: {file_size} bytes")
            return True
        except requests.RequestException:
            pass

        try:
            response = requests.get(
                url,
                timeout=self.default_timeout,
                allow_redirects=True,
                headers={**self._headers, "Range": "bytes=0-1"},
                stream=True,
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            return any(token in content_type for token in ("audio", "video", "octet-stream"))
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
        progress_callback: Callable[[float, float], None] | None = None,
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
