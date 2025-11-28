"""Instagram downloader service implementation."""

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
            logger.error(f"Error downloading from Instagram: {str(e)}", exc_info=True)
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

            if post.is_video:
                # Download video
                video_url = post.video_url
                filename = self.file_service.sanitize_filename(os.path.basename(save_path) + ".mp4")
                full_path = os.path.join(save_dir, filename)

                result = file_service.download_file(video_url, full_path, progress_callback)
                return result.success
            else:
                # Download image(s) - handle both single images and carousels
                success = False

                # Check if it's a sidecar (carousel) post
                if post.typename == "GraphSidecar":
                    for i, node in enumerate(post.get_sidecar_nodes()):
                        try:
                            # Get URL based on media type
                            if node.is_video:
                                media_url = node.video_url
                                ext = ".mp4"
                            else:
                                media_url = node.display_url
                                ext = ".jpg"

                            # Generate filename
                            if i > 0:
                                filename = self.file_service.sanitize_filename(
                                    f"{os.path.basename(save_path)}_{i}{ext}"
                                )
                            else:
                                filename = self.file_service.sanitize_filename(
                                    f"{os.path.basename(save_path)}{ext}"
                                )

                            full_path = os.path.join(save_dir, filename)
                            result = file_service.download_file(
                                media_url, full_path, progress_callback
                            )
                            if result.success:
                                success = True
                        except Exception as e:
                            logger.error(f"Error downloading sidecar item {i}: {str(e)}")
                            continue
                else:
                    # Single image post
                    image_url = post.url
                    filename = self.file_service.sanitize_filename(
                        f"{os.path.basename(save_path)}.jpg"
                    )
                    full_path = os.path.join(save_dir, filename)
                    result = file_service.download_file(image_url, full_path, progress_callback)
                    success = result.success

                return success

        except Exception as e:
            logger.error(f"Error downloading Instagram post: {str(e)}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, f"Downloading Instagram post {shortcode}", "Instagram"
                )
            return False
