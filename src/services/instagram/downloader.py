import os
import time
from collections.abc import Callable
from urllib.parse import urlparse

import instaloader

from src.core.config import AppConfig, get_config
from src.core.interfaces import BaseDownloader, IErrorNotifier, IFileService

from ...core.enums import ServiceType
from ...utils.logger import get_logger
from ..file.service import FileService
from ..network.checker import check_site_connection

logger = get_logger(__name__)


class InstagramDownloader(BaseDownloader):
    """Instagram downloader service with authentication support."""

    def __init__(
        self,
        error_handler: IErrorNotifier | None = None,
        file_service: IFileService | None = None,
        config: AppConfig = get_config(),
    ):
        """Initialize Instagram downloader.

        Args:
            error_handler: Optional error handler for user notifications
            file_service: Optional file service for file operations
            config: AppConfig instance (defaults to get_config() if None)
        """
        super().__init__(error_handler, file_service, config)
        self.loader = None
        self.authenticated = False
        self.login_attempts = 0
        self.max_login_attempts = self.config.instagram.max_login_attempts
        self.last_login_attempt = 0
        if not self.file_service:
            self.file_service = FileService()

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with Instagram.

        Args:
            username: Instagram username
            password: Instagram password

        Returns:
            True if authentication was successful, False otherwise
        """
        logger.info(f"[INSTAGRAM_DOWNLOADER] Starting authentication for user: {username[:3]}***")

        # Check if we've tried too many times recently
        current_time = time.time()
        if (
            self.login_attempts >= self.max_login_attempts
            and current_time - self.last_login_attempt
            < self.config.instagram.login_cooldown_seconds
        ):
            error_msg = "Too many login attempts. Please try again later."
            logger.error(error_msg)
            return False

        connected, error_msg = check_site_connection(ServiceType.INSTAGRAM)
        if not connected:
            logger.error(f"Cannot authenticate with Instagram: {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Instagram", "authentication", error_msg or "Connection failed", ""
                )
            return False

        self.login_attempts += 1
        self.last_login_attempt = time.time()

        try:
            logger.info("[INSTAGRAM_DOWNLOADER] Creating Instaloader instance")
            # Use realistic browser User-Agent to avoid 400 errors
            user_agent = self.config.network.cookie_user_agent

            self.loader = instaloader.Instaloader(
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                quiet=True,
                user_agent=user_agent,
            )

            logger.info("[INSTAGRAM_DOWNLOADER] Attempting login with Instagram")
            self.loader.login(username, password)
            self.authenticated = True
            logger.info("[INSTAGRAM_DOWNLOADER] ✅ Instagram authentication successful")
            return True

        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__

            # Truncate very long error messages (e.g., challenge URLs)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."

            logger.error(f"[INSTAGRAM_DOWNLOADER] ❌ Instagram authentication failed: {error_msg}")
            logger.error(f"[INSTAGRAM_DOWNLOADER] Exception type: {error_type}")

            self.authenticated = False
            if self.error_handler:
                self.error_handler.handle_exception(e, "Instagram authentication", "Instagram")
            return False

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """
        Download media from Instagram URLs.

        Args:
            url: Instagram URL to download from
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates

        Returns:
            True if download was successful, False otherwise
        """
        try:
            connected, error_msg = check_site_connection(ServiceType.INSTAGRAM)
            if not connected:
                logger.error(f"Cannot download from Instagram: {error_msg}")
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram", "download", error_msg or "Connection failed", url
                    )
                return False

            # Initialize instaloader if not already done
            if not self.loader:
                # Use realistic browser User-Agent to avoid 400 errors
                user_agent = self.config.network.cookie_user_agent

                self.loader = instaloader.Instaloader(
                    download_videos=True,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                    quiet=True,
                    user_agent=user_agent,
                )

            # Parse URL to determine content type
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")

            if len(path_parts) < 2:
                error_msg = "Invalid Instagram URL format"
                logger.error(error_msg)
                if self.error_handler:
                    self.error_handler.handle_service_failure(
                        "Instagram", "download", error_msg, url
                    )
                return False

            content_type = path_parts[0]
            shortcode = path_parts[1]

            # Use set for O(1) membership check instead of O(n) list check
            post_content_types = {"p", "reel"}
            if content_type in post_content_types:
                return self._download_post(shortcode, save_path, progress_callback)

            error_msg = f"Unsupported Instagram content type: {content_type}"
            logger.error(error_msg)
            if self.error_handler:
                self.error_handler.handle_service_failure("Instagram", "download", error_msg, url)
                return False

        except Exception as e:
            logger.error(f"Error downloading from Instagram: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Instagram download", "Instagram")
            return False

    def _download_post(
        self,
        shortcode: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """Download a single Instagram post or reel."""
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            file_service = FileService()
            save_dir = os.path.dirname(save_path) if os.path.dirname(save_path) else "."
            self.file_service.ensure_directory(save_dir)

            base_name = os.path.basename(save_path)
            media_success = False

            if post.is_video:
                video_url = post.video_url
                filename = self.file_service.sanitize_filename(f"{base_name}.mp4")
                full_path = os.path.join(save_dir, filename)
                result = file_service.download_file(video_url, full_path, progress_callback)
                media_success = result.success
            elif post.typename == "GraphSidecar":
                for i, node in enumerate(post.get_sidecar_nodes()):
                    try:
                        ext = ".mp4" if node.is_video else ".jpg"
                        media_url = node.video_url if node.is_video else node.display_url
                        suffix = f"_{i}" if i > 0 else ""
                        filename = self.file_service.sanitize_filename(f"{base_name}{suffix}{ext}")
                        full_path = os.path.join(save_dir, filename)
                        result = file_service.download_file(media_url, full_path, progress_callback)
                        if result.success:
                            media_success = True
                    except Exception as e:
                        logger.error(f"Error downloading sidecar item {i}: {e!s}")
                        continue
            else:
                image_url = post.url
                filename = self.file_service.sanitize_filename(f"{base_name}.jpg")
                full_path = os.path.join(save_dir, filename)
                result = file_service.download_file(image_url, full_path, progress_callback)
                media_success = result.success

            caption = post.caption
            if caption:
                caption_filename = self.file_service.sanitize_filename(f"{base_name}_caption.txt")
                caption_path = os.path.join(save_dir, caption_filename)
                self.file_service.save_text_file(caption, caption_path)

            return media_success

        except Exception as e:
            logger.error(f"Error downloading Instagram post: {e!s}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, f"Downloading Instagram post {shortcode}", "Instagram"
                )
            return False
