import instaloader
import os
import logging
from tkinter import messagebox
from urllib.parse import urlparse

from src.utils.common import download_file, get_file_extension, sanitize_filename

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InstagramDownloader:
    def __init__(self):
        self.insta_loader = instaloader.Instaloader()
        self.is_authenticated = False

    def authenticate(self, username, password):
        """Authenticate user with Instagram."""
        try:
            self.insta_loader.login(username, password)
            self.is_authenticated = True
            logger.info(f"Successfully authenticated Instagram user: {username}")
        except instaloader.exceptions.BadCredentialsException:
            logger.error("Invalid username or password")
            messagebox.showerror("Authentication Error", "Invalid username or password")
        except Exception as e:
            logger.error(f"An error occurred during authentication: {str(e)}")
            messagebox.showerror("Authentication Error", f"An error occurred during authentication: {str(e)}")

    def download_media(self, media_url, filename):
        """Download a media file from a given URL."""
        extension = get_file_extension(media_url) or '.jpg'
        sanitized_filename = sanitize_filename(f"{os.path.basename(filename)}{extension}")
        full_save_path = os.path.join(os.path.dirname(filename), sanitized_filename)
        return download_file(media_url, full_save_path)

    def download_instagram_media(self, link, save_path):
        """Download media from Instagram link."""
        if not self.is_authenticated:
            logger.error("Please log in to Instagram first")
            messagebox.showerror("Authentication Required", "Please log in to Instagram first")
            return False

        try:
            shortcode = self.extract_shortcode(link)
            if not shortcode:
                raise ValueError("Invalid Instagram URL")

            post = instaloader.Post.from_shortcode(self.insta_loader.context, shortcode)
            self.handle_post_media(post, save_path)
            self.download_caption(post, save_path)

            logger.info(f"Instagram media downloaded successfully as {save_path}")
            messagebox.showinfo("Success", f"Instagram media downloaded successfully as {save_path}")
            return True
        except ValueError as ve:
            logger.error(f"Invalid URL provided: {str(ve)}")
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            logger.error(f"Error downloading Instagram media: {str(e)}")
            messagebox.showerror("Download Error", f"Error downloading Instagram media: {str(e)}")
        return False

    def extract_shortcode(self, link):
        """Extract the shortcode from the Instagram link."""
        parsed_url = urlparse(link)
        path_parts = parsed_url.path.strip('/').split('/')
        if 'p' in path_parts:
            return path_parts[path_parts.index('p') + 1]
        elif 'reel' in path_parts:
            return path_parts[path_parts.index('reel') + 1]
        return None

    def handle_post_media(self, post, save_path):
        """Handle downloading of media from a post."""
        if post.typename == 'GraphSidecar':
            for i, node in enumerate(post.get_sidecar_nodes()):
                filename = f"{save_path}_slide_{i + 1}"
                if node.is_video:
                    self.download_media(node.video_url, f"{filename}.mp4")
                else:
                    self.download_media(node.display_url, f"{filename}.jpg")
        elif post.is_video:
            self.download_media(post.video_url, f"{save_path}.mp4")
        else:
            self.download_media(post.url, f"{save_path}.jpg")

    def download_caption(self, post, save_path):
        """Download the caption of a post."""
        caption_path = f"{save_path}_caption.txt"
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write(post.caption or "No caption")


# Usage example
if __name__ == "__main__":
    downloader = InstagramDownloader()
    username = "your_username"
    password = "your_password"
    downloader.authenticate(username, password)
    downloader.download_instagram_media("https://www.instagram.com/p/shortcode/", "./downloaded_media")