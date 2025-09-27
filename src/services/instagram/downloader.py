"""Instagram downloader service implementation."""

import instaloader
import logging
import os
import time
from typing import Callable, Optional
from urllib.parse import urlparse

from ...core import BaseDownloader
from ...utils.common import download_file, sanitize_filename, check_site_connection

logger = logging.getLogger(__name__)


class InstagramDownloader(BaseDownloader):
    """Instagram downloader service with authentication support."""

    def __init__(self):
        self.loader = None
        self.authenticated = False
        self.login_attempts = 0
        self.max_login_attempts = 3
        self.last_login_attempt = 0

    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate with Instagram.

        Args:
            username: Instagram username
            password: Instagram password

        Returns:
            True if authentication was successful, False otherwise
        """
        # Check if we've tried too many times recently
        current_time = time.time()
        if self.login_attempts >= self.max_login_attempts and current_time - self.last_login_attempt < 600:  # 10 minutes
            logger.error("Too many login attempts. Please try again later.")
            return False

        # First check internet connectivity to Instagram
        connected, error_msg = check_site_connection("Instagram")
        if not connected:
            logger.error(f"Cannot authenticate with Instagram: {error_msg}")
            return False

        self.login_attempts += 1
        self.last_login_attempt = time.time()

        try:
            self.loader = instaloader.Instaloader(
                download_videos=True,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                quiet_mode=True
            )

            self.loader.login(username, password)
            self.authenticated = True
            logger.info("Instagram authentication successful")
            return True

        except Exception as e:
            logger.error(f"Instagram authentication failed: {str(e)}")
            self.authenticated = False
            return False

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
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
            # Check connectivity to Instagram
            connected, error_msg = check_site_connection("Instagram")
            if not connected:
                logger.error(f"Cannot download from Instagram: {error_msg}")
                return False

            # Initialize instaloader if not already done
            if not self.loader:
                self.loader = instaloader.Instaloader(
                    download_videos=True,
                    download_video_thumbnails=False,
                    download_geotags=False,
                    download_comments=False,
                    save_metadata=False,
                    quiet_mode=True
                )

            # Parse URL to determine content type
            parsed = urlparse(url)
            path_parts = parsed.path.strip('/').split('/')

            if len(path_parts) < 2:
                logger.error("Invalid Instagram URL format")
                return False

            content_type = path_parts[0]  # 'p' for posts, 'reel' for reels
            shortcode = path_parts[1]

            # Download based on content type
            if content_type in ['p', 'reel']:
                return self._download_post(shortcode, save_path, progress_callback)
            else:
                logger.error(f"Unsupported Instagram content type: {content_type}")
                return False

        except Exception as e:
            logger.error(f"Error downloading from Instagram: {str(e)}")
            return False

    def _download_post(
        self,
        shortcode: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """Download a single Instagram post or reel."""
        try:
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            if post.is_video:
                # Download video
                video_url = post.video_url
                save_dir = os.path.dirname(save_path)
                filename = sanitize_filename(os.path.basename(save_path) + '.mp4')
                full_path = os.path.join(save_dir, filename)

                return download_file(video_url, full_path, progress_callback)
            else:
                # Download image(s)
                save_dir = os.path.dirname(save_path)
                success = False

                for i, url in enumerate(post.get_sidecar_nodes()):
                    ext = '.jpg'
                    if i > 0:
                        filename = sanitize_filename(f"{os.path.basename(save_path)}_{i}{ext}")
                    else:
                        filename = sanitize_filename(f"{os.path.basename(save_path)}{ext}")

                    full_path = os.path.join(save_dir, filename)
                    if download_file(url, full_path, progress_callback):
                        success = True

                return success

        except Exception as e:
            logger.error(f"Error downloading Instagram post: {str(e)}")
            return False