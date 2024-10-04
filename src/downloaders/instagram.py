import instaloader
from tkinter import messagebox
import os
from urllib.parse import urlparse
import logging

from src.utils.common import download_file, get_file_extension, sanitize_filename

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

insta_loader = None


def authenticate_instagram(username, password):
    global insta_loader
    insta_loader = instaloader.Instaloader()
    try:
        insta_loader.login(username, password)
        logger.info(f"Successfully authenticated Instagram user: {username}")
        return True
    except instaloader.exceptions.BadCredentialsException:
        error_message = "Invalid username or password"
        logger.error(error_message)
        messagebox.showerror("Authentication Error", error_message)
    except Exception as e:
        error_message = f"An error occurred during authentication: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Authentication Error", error_message)


def download_instagram_media(link, save_path):
    global insta_loader
    if not insta_loader:
        error_message = "Please log in to Instagram first"
        logger.error(error_message)
        messagebox.showerror("Authentication Required", error_message)
        return

    try:
        parsed_url = urlparse(link)
        path_parts = parsed_url.path.strip('/').split('/')

        # Extract shortcode from the URL
        if 'p' in path_parts:
            shortcode = path_parts[path_parts.index('p') + 1]
        elif 'reel' in path_parts:
            shortcode = path_parts[path_parts.index('reel') + 1]
        else:
            raise ValueError("Invalid Instagram URL")

        post = instaloader.Post.from_shortcode(insta_loader.context , shortcode)

        # Handle different types of posts
        if post.typename == 'GraphSidecar':  # Carousel (multiple media)
            for i, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    download_media(node.video_url, f"{save_path}_slide_{i + 1}.mp4")
                else:
                    download_media(node.display_url, f"{save_path}_slide_{i + 1}.jpg")
        elif post.is_video:  # Single video post
            download_media(post.video_url, f"{save_path}.mp4")
        else:  # Single image post
            download_media(post.url, f"{save_path}.jpg")

        # Download caption as a text file
        caption_path = f"{save_path}_caption.txt"
        with open(caption_path, "w", encoding="utf-8") as f:
            f.write(post.caption or "No caption")

        success_message = f"Instagram media downloaded successfully as {save_path}"
        logger.info(success_message)
        messagebox.showinfo("Success", success_message)
        return True
    except ValueError as ve:
        logger.error(f"Invalid URL provided: {str(ve)}")
        messagebox.showerror("Error", str(ve))
        return False
    except Exception as e:
        error_message = f"Error downloading Instagram media: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Download Error", error_message)
        return False


def download_media(media_url, filename):
    extension = get_file_extension(media_url) or '.jpg'
    sanitized_filename = sanitize_filename(f'{os.path.basename(filename)}{extension}')
    full_save_path = os.path.join(os.path.dirname(filename), sanitized_filename)
    return download_file(media_url, full_save_path)
