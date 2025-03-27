import instaloader
import logging
import os
import time
from typing import Callable, Optional
from urllib.parse import urlparse

from src.utils.common import download_file, sanitize_filename, check_site_connection
from .base import BaseDownloader

logger = logging.getLogger(__name__)


class InstagramDownloader(BaseDownloader):
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
                compress_json=False,
                max_connection_attempts=3,  # Connection attempts
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            
            # Try to login with rate limiting awareness
            self.loader.login(username, password)
            self.authenticated = True
            self.login_attempts = 0  # Reset counter on success
            logger.info(f"Successfully authenticated as {username}")
            return True
            
        except instaloader.exceptions.ConnectionException as e:
            logger.error(f"Instagram connection error: {str(e)}")
            return False
        except instaloader.exceptions.BadCredentialsException:
            logger.error("Invalid Instagram credentials")
            return False
        except instaloader.exceptions.TwoFactorAuthRequiredException:
            logger.error("Two-factor authentication required")
            return False
        except instaloader.exceptions.InvalidArgumentException as e:
            logger.error(f"Invalid argument: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            self.authenticated = False
            return False

    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Download content from Instagram.
        
        Args:
            url: Instagram URL to download
            save_path: Path to save the downloaded content
            progress_callback: Callback for progress updates
            
        Returns:
            True if download was successful, False otherwise
        """
        # Check authentication
        if not self.authenticated or not self.loader:
            logger.error("Not authenticated with Instagram")
            return False
            
        # Check internet connectivity to Instagram
        connected, error_msg = check_site_connection("Instagram")
        if not connected:
            logger.error(f"Cannot download from Instagram: {error_msg}")
            return False

        try:
            # Extract post shortcode
            shortcode = self._extract_shortcode(url)
            if not shortcode:
                logger.error(f"Could not extract Instagram shortcode from URL: {url}")
                return False

            # Get post
            try:
                logger.debug(f"Retrieving Instagram post {shortcode}...")
                post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            except instaloader.exceptions.ConnectionException as e:
                # Retry with backoff
                logger.warning(f"Connection error retrieving post, retrying: {str(e)}")
                time.sleep(2)
                try:
                    post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to get Instagram post after retry: {error_msg}")
                    return False

            # Handle different post types
            if post.typename == 'GraphSidecar':  # Multiple images/videos
                logger.info(f"Downloading Instagram carousel with {post.mediacount} items")
                success = True
                for i, node in enumerate(post.get_sidecar_nodes()):
                    item_path = f"{save_path}_slide_{i + 1}"
                    if not self._download_node(node, item_path, progress_callback):
                        success = False
                        
                if success:
                    logger.info(f"Successfully downloaded Instagram carousel to {save_path}")
                return success
            else:  # Single image/video
                logger.info(f"Downloading Instagram {post.typename}")
                result = self._download_node(post, save_path, progress_callback)
                if result:
                    logger.info(f"Successfully downloaded Instagram post to {save_path}")
                return result

        except instaloader.exceptions.ConnectionException as e:
            error_msg = str(e)
            logger.error(f"Instagram connection error: {error_msg}")
            return False
        except instaloader.exceptions.InstaloaderException as e:
            error_msg = str(e)
            if "not find" in error_msg.lower() or "not exists" in error_msg.lower():
                logger.error("The Instagram post no longer exists or is private")
            else:
                logger.error(f"Instagram download error: {error_msg}")
            return False
        except Exception as e:
            logger.error(f"Error downloading from Instagram: {str(e)}")
            return False

    @staticmethod
    def _extract_shortcode(url: str) -> Optional[str]:
        """Extract the shortcode from an Instagram URL."""
        try:
            path = urlparse(url).path.strip('/').split('/')
            if 'p' in path:
                return path[path.index('p') + 1]
            elif 'reel' in path:
                return path[path.index('reel') + 1]
            elif 'tv' in path:
                return path[path.index('tv') + 1]
            return None
        except Exception as e:
            logger.error(f"Error extracting Instagram shortcode: {str(e)}")
            return None

    @staticmethod
    def _download_node(
            node,
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """Download a single node (photo or video)."""
        try:
            # Determine media type and URL
            if node.is_video:
                url = node.video_url
                ext = '.mp4'
            else:
                url = node.url
                ext = '.jpg'

            # Create filename
            filename = sanitize_filename(f'{os.path.basename(save_path)}{ext}')
            full_path = os.path.join(os.path.dirname(save_path), filename)
            
            # Download the file
            return download_file(url, full_path, progress_callback)
        except AttributeError as e:
            logger.error(f"Missing attribute on Instagram node: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error downloading Instagram node: {str(e)}")
            return False