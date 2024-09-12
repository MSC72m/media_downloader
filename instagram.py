import instaloader
from PyQt5.QtWidgets import QMessageBox
import requests
from operations import operations
import os

insta_loader = instaloader.Instaloader()

def download_instagram_video(link, save_name, progress_callback):
    try:
        shortcode = link.split('/')[-2]
        post = instaloader.Post.from_shortcode(insta_loader.context, shortcode)

        # Carousel post (multiple images/videos)
        if post.typename == 'GraphSidecar':
            for i, node in enumerate(post.get_sidecar_nodes()):
                if node.is_video:
                    video_url = node.video_url
                    download_video(video_url, f"{save_name}_slide_{i}", progress_callback)
                else:
                    photo_url = node.display_url
                    download_video(photo_url, f"{save_name}_slide_{i}", progress_callback)
        else:
            if post.is_video:  # Single video post
                video_url = post.video_url
                download_video(video_url, save_name, progress_callback)
            else:  # Single image post
                media_url = post.url
                download_video(media_url, save_name, progress_callback)

        QMessageBox.information(None, "Success", f"Instagram media downloaded successfully as {save_name}")
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Error downloading Instagram media: {str(e)}")
    finally:
        operations.on_operation_done()

def download_video(video_url, filename, progress_callback):
    try:
        response = requests.get(video_url, stream=True, timeout=10)
        response.raise_for_status()

        file_format = response.headers.get('Content-Type', '').split("/")[-1]
        if not file_format:
            file_format = 'mp4'

        full_filename = f"{filename}.{file_format}"
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 KB
        written = 0

        with open(full_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                f.write(chunk)
                written += len(chunk)
                if total_size > 0:
                    progress = int((written / total_size) * 100)
                    progress_callback.emit(progress)

        progress_callback.emit(100)  # Ensure 100% progress is emitted

    except requests.exceptions.RequestException as e:
        QMessageBox.critical(None, "Error", f"Error downloading media: {str(e)}")
    except IOError as e:
        QMessageBox.critical(None, "Error", f"Error saving media: {str(e)}")