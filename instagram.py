import instaloader
from tkinter import messagebox
import requests

insta_loader = instaloader.Instaloader()


def download_instagram_video(link):
    from oprations import on_operation_done
    try:
        shortcode = link.split('/')[-2]
        post = instaloader.Post.from_shortcode(insta_loader.context, shortcode)

        # Carousel post (multiple images/videos)
        if post.typename == 'GraphSidecar':

            for _, node in enumerate(post.get_sidecar_nodes()):

                if node.is_video:
                    video_url = node.video_url
                    download_video(video_url, f"insta_slide_{shortcode}_{_}")

                else:
                    photo_url = node.display_url
                    download_video(photo_url, f"insta_slide_{shortcode}_{_}")

        else:
            if post.is_video:  # Single video post
                video_url = post.video_url
                download_video(video_url, f"insta_slide_{shortcode}")

            else:  # Single image post
                media_url = post.url
                download_video(media_url, f"insta_slide_{shortcode}")

        messagebox.showinfo("Success", "Video downloaded successfully.")

        on_operation_done()
    except Exception as e:
        messagebox.showerror(
            "Error", f"Error downloading Instagram video: {e}")
        on_operation_done()


def download_video(video_url, filename):
    try:
        response = requests.get(video_url, stream=True)

        response.raise_for_status()

        file_format = response.headers.get('Content-Type').split("/")[1]

        home = ""
        with open(home + f"{filename}.{file_format}", 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Error downloading video: {e}")
    except IOError as e:
        messagebox.showerror("Error", f"Error saving video: {e}")

