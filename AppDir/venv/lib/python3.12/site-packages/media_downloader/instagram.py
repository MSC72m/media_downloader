import instaloader
import requests
from tkinter import messagebox
import os
from urllib.parse import urlparse
import logging

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

def download_instagram_media(link, save_name):
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

        post = instaloader.Post.from_shortcode(insta_loader.context, shortcode)

        # Handle different types of posts
        if post.typename == 'GraphSidecar':  # Carousel (multiple media)
            for i, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    download_media(node.video_url, f"{save_name}_slide_{i + 1}.mp4")
                else:
                    download_media(node.display_url, f"{save_name}_slide_{i + 1}.jpg")
        elif post.is_video:  # Single video post
            download_media(post.video_url, f"{save_name}.mp4")
        else:  # Single image post
            download_media(post.url, f"{save_name}.jpg")

        # Download caption as a text file
        with open(f"{save_name}_caption.txt", "w", encoding="utf-8") as f:
            f.write(post.caption or "No caption")

        success_message = f"Instagram media downloaded successfully as {save_name}"
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
    try:
        response = requests.get(media_url, stream=True, timeout=10)
        response.raise_for_status()

        # Save media content to file
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

        logger.info(f"Media downloaded and saved as {filename}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading media: {str(e)}")
        messagebox.showerror("Download Error", f"Error downloading media: {str(e)}")
    except IOError as e:
        logger.error(f"Error saving media: {str(e)}")
        messagebox.showerror("Save Error", f"Error saving media: {str(e)}")
