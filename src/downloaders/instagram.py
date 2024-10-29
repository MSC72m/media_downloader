import instaloader
import logging
import os
from typing import Callable, Optional
from urllib.parse import urlparse

from src.utils.common import download_file, sanitize_filename
from .base import BaseDownloader

logger = logging.getLogger(__name__)


class InstagramDownloader(BaseDownloader):
    def __init__(self):
        self.loader = None
        self.authenticated = False

    def authenticate(self, username: str, password: str) -> bool:
        try:
            self.loader = instaloader.Instaloader()
            self.loader.login(username, password)
            self.authenticated = True
            logger.info(f"Successfully authenticated as {username}")
            return True
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
        if not self.authenticated or not self.loader:
            logger.error("Not authenticated")
            return False

        try:
            shortcode = self._extract_shortcode(url)
            if not shortcode:
                return False

            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            # Handle different post types
            if post.typename == 'GraphSidecar':
                success = True
                for i, node in enumerate(post.get_sidecar_nodes()):
                    if not self._download_node(node, f"{save_path}_slide_{i + 1}", progress_callback):
                        success = False
                return success
            else:
                return self._download_node(post, save_path, progress_callback)

        except Exception as e:
            logger.error(f"Error downloading from Instagram: {str(e)}")
            return False

    @staticmethod
    def _extract_shortcode(url: str) -> Optional[str]:
        try:
            path = urlparse(url).path.strip('/').split('/')
            if 'p' in path:
                return path[path.index('p') + 1]
            elif 'reel' in path:
                return path[path.index('reel') + 1]
            return None
        except Exception:
            return None

    @staticmethod
    def _download_node(
            node,
            save_path: str,
            progress_callback: Optional[Callable[[float, float], None]]
    ) -> bool:
        try:
            if node.is_video:
                url = node.video_url
                ext = '.mp4'
            else:
                url = node.url
                ext = '.jpg'

            filename = sanitize_filename(f'{os.path.basename(save_path)}{ext}')
            full_path = os.path.join(os.path.dirname(save_path), filename)

            return download_file(url, full_path, progress_callback)

        except Exception as e:
            logger.error(f"Error downloading node: {str(e)}")
            return False