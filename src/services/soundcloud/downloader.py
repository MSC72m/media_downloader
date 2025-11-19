"""SoundCloud downloader service implementation."""

import os
import re
from typing import Any, Callable, Dict, Optional

import yt_dlp

from src.utils.logger import get_logger

from ...core.base import BaseDownloader

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
            save_path: Path to save the downloaded file (without extension)
            progress_callback: Optional callback for progress updates (progress%, speed)

        Returns:
            bool: True if download successful, False otherwise
        """
        if not url:
            logger.error("[SOUNDCLOUD_DOWNLOADER] No URL provided")
            return False

        # Create the output directory if it doesn't exist
        save_dir = os.path.dirname(save_path)
        if save_dir and not os.path.exists(save_dir):
            logger.error(
                f"[SOUNDCLOUD_DOWNLOADER] Save directory does not exist: {save_dir}"
            )
            return False

        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Starting download: {url}")
        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Save path: {save_path}")
        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Audio format: {self.audio_format}")
        logger.info(f"[SOUNDCLOUD_DOWNLOADER] Audio quality: {self.audio_quality}")

        # First, check if track is premium/Go+ only
        try:
            info = self.get_info(url)
            if info and self._is_premium_track(info):
                error_msg = (
                    "This track requires SoundCloud Go+ subscription and cannot be downloaded.\n\n"
                    "Premium tracks are not accessible without a paid subscription."
                )
                logger.warning(f"[SOUNDCLOUD_DOWNLOADER] Premium track detected: {url}")
                return False
        except Exception as check_error:
            logger.warning(
                f"[SOUNDCLOUD_DOWNLOADER] Could not check premium status: {check_error}"
            )
            # Continue with download attempt

        try:
            # Create progress hook
            progress_hook = self._create_progress_hook(progress_callback)

            # Configure options with save path and progress hook
            options = self.ytdl_opts.copy()
            # Use the provided save_path as the output template
            # yt-dlp will add the appropriate extension
            options["outtmpl"] = f"{save_path}.%(ext)s"
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

        except Exception as e:
            error_msg = str(e)

            # Use regex for efficient premium error detection
            premium_error_pattern = re.compile(
                r"\b(premium|go\+|subscription|not\s+available)\b", re.IGNORECASE
            )

            # Check for premium/Go+ errors first
            if premium_error_pattern.search(error_msg):
                logger.error(
                    f"[SOUNDCLOUD_DOWNLOADER] Premium content error: {error_msg}"
                )
                self._handle_download_error(error_msg)
                return False

            # Check if it's a DownloadError
            if "DownloadError" in type(e).__name__:
                logger.error(f"[SOUNDCLOUD_DOWNLOADER] Download error: {error_msg}")
                self._handle_download_error(error_msg)
            else:
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

    def _is_premium_track(self, info: Dict[str, Any]) -> bool:
        """Check if track requires SoundCloud Go+ subscription.

        Args:
            info: Track information dictionary

        Returns:
            True if track is premium/Go+ only
        """
        # Check various indicators of premium content
        if not info:
            return False

        # Check policy field which often indicates premium status
        if info.get("policy") == "BLOCK":
            return True

        # Check for premium keywords using efficient regex
        description = info.get("description") or ""
        title = info.get("title") or ""

        # Compile regex pattern for premium keywords (case-insensitive)
        premium_pattern = re.compile(
            r"\b(go\+|premium\s+only|subscribers?\s+only|subscription\s+required)\b",
            re.IGNORECASE,
        )

        if premium_pattern.search(description) or premium_pattern.search(title):
            return True

        # Check availability
        if not info.get("is_available", True):
            return True

        return False

    def _handle_download_error(self, error_msg: str) -> None:
        """Handle and classify download errors.

        Args:
            error_msg: Error message from yt-dlp
        """
        # Use regex patterns for efficient error classification
        error_patterns = {
            r"\b(premium|go\+|subscription\s+required)\b": "[SOUNDCLOUD_DOWNLOADER] Track requires SoundCloud Go+ subscription",
            r"\b(private|not\s+available)\b": "[SOUNDCLOUD_DOWNLOADER] Track is private or not available",
            r"\bcopyright\b": "[SOUNDCLOUD_DOWNLOADER] Copyright restriction",
            r"\b(geo|region)\b": "[SOUNDCLOUD_DOWNLOADER] Geographic restriction",
            r"\b(network|connection)\b": "[SOUNDCLOUD_DOWNLOADER] Network connection error",
            r"\b(403|401)\b": "[SOUNDCLOUD_DOWNLOADER] Access denied - authentication may be required",
            r"\b404\b": "[SOUNDCLOUD_DOWNLOADER] Track not found",
        }

        # Check each pattern
        for pattern, log_message in error_patterns.items():
            if re.search(pattern, error_msg, re.IGNORECASE):
                logger.error(log_message)
                return

        # If no pattern matches, log as unknown error
        logger.error(f"[SOUNDCLOUD_DOWNLOADER] Unknown error: {error_msg}")

    def get_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get information about a SoundCloud track without downloading.

        Args:
            url: SoundCloud URL

        Returns:
            Dictionary with track information or None if failed
        """
        try:
            with yt_dlp.YoutubeDL(
                {
                    "quiet": True,
                    "no_warnings": True,
                    "extract_flat": False,
                }
            ) as ydl:
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
                    "is_available": info.get("availability") != "premium_only",
                    "policy": info.get("policy", ""),
                }

        except Exception as e:
            logger.error(
                f"[SOUNDCLOUD_DOWNLOADER] Error getting info: {e}", exc_info=True
            )
            return None
