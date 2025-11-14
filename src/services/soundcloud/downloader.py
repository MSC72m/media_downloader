"""SoundCloud downloader service implementation."""

import os
from typing import Any, Callable, Dict, Optional

import yt_dlp

from src.utils.logger import get_logger

from ...core.base import BaseDownloader
from ...core.enums import ServiceType
from ..file.sanitizer import FilenameSanitizer

logger = get_logger(__name__)


class SoundCloudDownloader(BaseDownloader):
    """SoundCloud downloader service using yt-dlp."""

    def __init__(
        self,
        audio_format: str = "mp3",
        audio_quality: str = "best",
        download_playlist: bool = False,
        embed_metadata: bool = True,
        download_thumbnail: bool = True,
        speed_limit: Optional[int] = None,
        retries: int = 3,
    ):
        """Initialize SoundCloud downloader.

        Args:
            audio_format: Output audio format (mp3, aac, wav, etc.)
            audio_quality: Audio quality (best, 320, 256, 192, 128)
            download_playlist: Whether to download entire playlists/sets
            embed_metadata: Whether to embed metadata in audio files
            download_thumbnail: Whether to download artwork/thumbnail
            speed_limit: Speed limit in KB/s (None for unlimited)
            retries: Number of retries on failure
        """
        self.audio_format = audio_format
        self.audio_quality = audio_quality
        self.download_playlist = download_playlist
        self.embed_metadata = embed_metadata
        self.download_thumbnail = download_thumbnail
        self.speed_limit = speed_limit
        self.retries = retries
        self.ytdl_opts = self._get_ytdl_options()

    def _get_ytdl_options(self) -> Dict[str, Any]:
        """Generate yt-dlp options for SoundCloud."""
        options = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "retries": self.retries,
            "fragment_retries": self.retries,
            "socket_timeout": 15,
            "extractor_retries": self.retries,
            "nocheckcertificate": True,
            "writethumbnail": self.download_thumbnail,
            "embedmetadata": self.embed_metadata,
            "postprocessors": [],
        }

        # Audio conversion settings
        audio_quality_map = {
            "best": "0",
            "320": "320",
            "256": "256",
            "192": "192",
            "128": "128",
        }

        quality_value = audio_quality_map.get(self.audio_quality, "0")

        options["postprocessors"].append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_format,
                "preferredquality": quality_value,
            }
        )

        # Embed thumbnail in audio file
        if self.download_thumbnail and self.embed_metadata:
            options["postprocessors"].append(
                {
                    "key": "EmbedThumbnail",
                    "already_have_thumbnail": False,
                }
            )

        # Add metadata
        if self.embed_metadata:
            options["postprocessors"].append(
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                }
            )

        # Speed limit
        if self.speed_limit:
            options["ratelimit"] = self.speed_limit * 1024  # KB/s to bytes/s

        # Playlist handling
        if not self.download_playlist:
            options["noplaylist"] = True
            options["playlist_items"] = "1"

        return options

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None,
    ) -> bool:
        """Download a SoundCloud track or playlist.

        Args:
            url: SoundCloud URL to download
            save_path: Directory to save the downloaded file
            progress_callback: Optional callback for progress updates (progress%, speed)

        Returns:
            bool: True if download successful, False otherwise
        """
        if not url:
            logger.error("[SOUNDCLOUD_DOWNLOADER] No URL provided")
            return False

        if not os.path.exists(save_path):
            logger.error(
                f"[SOUNDCLOUD_DOWNLOADER] Save path does not exist: {save_path}"
            )
            return False

        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Starting download: {url}")
        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Save path: {save_path}")
        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Audio format: {self.audio_format}")
        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Audio quality: {self.audio_quality}")

        try:
            # Create progress hook
            progress_hook = self._create_progress_hook(progress_callback)

            # Configure options with save path and progress hook
            options = self.ytdl_opts.copy()
            options["outtmpl"] = os.path.join(
                save_path, "%(uploader)s - %(title)s.%(ext)s"
            )
            options["progress_hooks"] = [progress_hook]

            # Attempt download
            with yt_dlp.YoutubeDL(options) as ydl:
                logger.info("[SOUNDCLOUD_DOWNLOADER] Extracting info...")
                info = ydl.extract_info(url, download=True)

                if not info:
                    logger.error("[SOUNDCLOUD_DOWNLOADER] Failed to extract info")
                    return False

                logger.info("[SOUNDCLOUD_DOWNLOADER] Download completed successfully")

                # Log download info
                if "title" in info:
                    logger.info(f"[SOUNDCLOUD_DOWNLOADER] Downloaded: {info['title']}")
                if "uploader" in info:
                    logger.info(f"[SOUNDCLOUD_DOWNLOADER] Artist: {info['uploader']}")

                return True

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"[SOUNDCLOUD_DOWNLOADER] Download error: {error_msg}")
            self._handle_download_error(error_msg)
            return False

        except Exception as e:
            logger.error(
                f"[SOUNDCLOUD_DOWNLOADER] Unexpected error: {e}", exc_info=True
            )
            return False

    def _create_progress_hook(
        self, progress_callback: Optional[Callable[[float, float], None]]
    ) -> Callable:
        """Create progress hook for yt-dlp.

        Args:
            progress_callback: Optional callback to call with progress updates

        Returns:
            Progress hook function
        """

        def hook(d: Dict[str, Any]) -> None:
            """Progress hook called by yt-dlp."""
            if not progress_callback:
                return

            status = d.get("status")

            if status == "downloading":
                # Calculate progress
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)

                if total > 0:
                    progress = (downloaded / total) * 100.0
                else:
                    progress = 0.0

                # Get speed
                speed = d.get("speed", 0) or 0
                speed_mbps = speed / (1024 * 1024) if speed else 0.0

                # Call progress callback
                try:
                    progress_callback(progress, speed_mbps)
                except Exception as e:
                    logger.error(
                        f"[SOUNDCLOUD_DOWNLOADER] Progress callback error: {e}"
                    )

            elif status == "finished":
                # Download finished, post-processing may follow
                try:
                    progress_callback(100.0, 0.0)
                except Exception as e:
                    logger.error(
                        f"[SOUNDCLOUD_DOWNLOADER] Progress callback error: {e}"
                    )

        return hook

    def _handle_download_error(self, error_msg: str) -> None:
        """Handle and classify download errors.

        Args:
            error_msg: Error message from yt-dlp
        """
        error_lower = error_msg.lower()

        if "private" in error_lower or "not available" in error_lower:
            logger.error("[SOUNDCLOUD_DOWNLOADER] Track is private or not available")
        elif "copyright" in error_lower:
            logger.error("[SOUNDCLOUD_DOWNLOADER] Copyright restriction")
        elif "geo" in error_lower or "region" in error_lower:
            logger.error("[SOUNDCLOUD_DOWNLOADER] Geographic restriction")
        elif "network" in error_lower or "connection" in error_lower:
            logger.error("[SOUNDCLOUD_DOWNLOADER] Network connection error")
        elif "403" in error_msg or "401" in error_msg:
            logger.error(
                "[SOUNDCLOUD_DOWNLOADER] Access denied - authentication may be required"
            )
        elif "404" in error_msg:
            logger.error("[SOUNDCLOUD_DOWNLOADER] Track not found")
        else:
            logger.error(f"[SOUNDCLOUD_DOWNLOADER] Unknown error: {error_msg}")

    def get_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get information about a SoundCloud track without downloading.

        Args:
            url: SoundCloud URL

        Returns:
            Dictionary with track information or None if failed
        """
        try:
            options = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

                if not info:
                    return None

                return {
                    "title": info.get("title", "Unknown"),
                    "artist": info.get("uploader", "Unknown"),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "description": info.get("description", ""),
                    "upload_date": info.get("upload_date", ""),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "is_playlist": "entries" in info,
                    "track_count": len(info.get("entries", []))
                    if "entries" in info
                    else 1,
                }

        except Exception as e:
            logger.error(
                f"[SOUNDCLOUD_DOWNLOADER] Error getting info: {e}", exc_info=True
            )
            return None
