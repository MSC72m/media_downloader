import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp

from src.core.config import AppConfig, get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TikTokDownloader(BaseDownloader):
    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config=None,
    ):
        if config is None:
            config = get_config()
        super().__init__(error_handler, file_service, config)
        self.default_timeout = config.tiktok.default_timeout
        self.max_retries = config.tiktok.max_retries

    def _get_ytdl_options(self) -> dict[str, Any]:
        """Generate yt-dlp options for TikTok."""
        return {
            "format": "best",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "retries": self.max_retries,
            "socket_timeout": self.default_timeout,
            "extractor_args": {
                "tiktok": {
                    "enable_download": True,
                    "enable_music": True,
                    "enable_subtitles": True,
                    "enable_metadata": True,
                    "download_thumbnail": True,
                }
            },
        }

    def _validate_download_inputs(self, url: str, save_path: str) -> bool:
        """Validate download inputs.

        Args:
            url: URL to download
            save_path: Path to save file

        Returns:
            True if valid, False otherwise
        """
        if not url:
            error_msg = "No URL provided"
            logger.error(f"[TIKTOK_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("TikTok", "download", error_msg, "")
            return False

        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            error_msg = f"Save directory does not exist: {save_dir}"
            logger.error(f"[TIKTOK_DOWNLOADER] {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("TikTok", "download", error_msg, url)
            return False

        return True

    def _perform_download(
        self, url: str, save_path: str, progress_callback: Callable[[float, float], None] | None
    ) -> bool:
        """Perform actual download.

        Args:
            url: TikTok URL
            save_path: Path to save file
            progress_callback: Progress callback

        Returns:
            True if successful, False otherwise
        """
        try:
            progress_hook = self._create_progress_hook(progress_callback)
            options = self._get_ytdl_options()
            options["outtmpl"] = f"{save_path}.%(ext)s"
            options["progress_hooks"] = [progress_hook]

            with yt_dlp.YoutubeDL(options) as ydl:
                logger.info("[TIKTOK_DOWNLOADER] Extracting info...")
                info = ydl.extract_info(url, download=True)

                if not info:
                    error_msg = "Failed to extract video information"
                    logger.error(f"[TIKTOK_DOWNLOADER] {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "TikTok", "download", error_msg, url
                        )
                    return False

                logger.info("[TIKTOK_DOWNLOADER] Download completed successfully")
                if "title" in info:
                    logger.info(f"[TIKTOK_DOWNLOADER] Downloaded: {info['title']}")
                return True

        except Exception as e:
            logger.error(f"[TIKTOK_DOWNLOADER] Download error: {e}", exc_info=True)
            return False

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] = None,
    ) -> bool:
        """Download a TikTok video.

        Args:
            url: TikTok URL to download
            save_path: Path to save downloaded file (without extension)
            progress_callback: Optional callback for progress updates (progress%, speed)

        Returns:
            bool: True if download successful, False otherwise
        """
        if not self._validate_download_inputs(url, save_path):
            return False

        logger.info(f"[TIKTOK_DOWNLOADER] Starting download: {url}")
        logger.info(f"[TIKTOK_DOWNLOADER] Save path: {save_path}")

        return self._perform_download(url, save_path, progress_callback)

    def _create_progress_hook(
        self, progress_callback: Callable[[float, float], None] | None
    ) -> Callable:
        """Create progress hook for yt-dlp.

        Args:
            progress_callback: Optional callback to call with progress updates

        Returns:
            Progress hook function
        """

        def hook(d: dict[str, Any]) -> None:
            """Progress hook called by yt-dlp."""
            if not progress_callback:
                return

            status = d.get("status")

            if status == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                progress = downloaded / total * 100.0 if total > 0 else 0.0

                speed = d.get("speed", 0) or 0
                mb_to_bytes = self.config.downloads.kb_to_bytes * 1024
                speed_mbps = speed / mb_to_bytes if speed else 0.0

                try:
                    progress_callback(progress, speed_mbps)
                except Exception as e:
                    logger.error(f"[TIKTOK_DOWNLOADER] Progress callback error: {e}")

            elif status == "finished":
                try:
                    progress_callback(100.0, 0.0)
                except Exception as e:
                    logger.error(f"[TIKTOK_DOWNLOADER] Progress callback error: {e}")

        return hook
