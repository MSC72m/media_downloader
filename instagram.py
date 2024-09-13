import instaloader
import requests
from tkinter import messagebox
import os
from urllib.parse import urlparse

insta_loader = None


def authenticate_instagram(username, password):
    global insta_loader
    insta_loader = instaloader.Instaloader()
    try:
        insta_loader.login(username, password)
        return True
    except instaloader.exceptions.BadCredentialsException:
        messagebox.showerror("Authentication Error", "Invalid username or password")
        return False
    except Exception as e:
        messagebox.showerror("Authentication Error", f"An error occurred: {str(e)}")
        return False


def download_instagram_media(link, save_name):
    global insta_loader
    if not insta_loader:
        messagebox.showerror("Authentication Required", "Please log in to Instagram first")
        return

    try:
        parsed_url = urlparse(link)
        path_parts = parsed_url.path.strip('/').split('/')

        if 'p' in path_parts:
            shortcode = path_parts[path_parts.index('p') + 1]
        elif 'reel' in path_parts:
            shortcode = path_parts[path_parts.index('reel') + 1]
        else:
            raise ValueError("Invalid Instagram URL")

        post = instaloader.Post.from_shortcode(insta_loader.context, shortcode)

        if post.typename == 'GraphSidecar':
            for i, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    download_media(node.video_url, f"{save_name}_slide_{i + 1}.mp4")
                else:
                    download_media(node.display_url, f"{save_name}_slide_{i + 1}.jpg")
        elif post.is_video:
            download_media(post.video_url, f"{save_name}.mp4")
        else:
            download_media(post.url, f"{save_name}.jpg")

        # Download caption
        with open(f"{save_name}_caption.txt", "w", encoding="utf-8") as f:
            f.write(post.caption or "No caption")

        messagebox.showinfo("Success", f"Instagram media downloaded successfully as {save_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading Instagram media: {str(e)}")


def download_media(media_url, filename):
    try:
        response = requests.get(media_url, stream=True, timeout=10)
        response.raise_for_status()

        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Error downloading media: {str(e)}")
    except IOError as e:
        messagebox.showerror("Error", f"Error saving media: {str(e)}")