import requests
from bs4 import BeautifulSoup
import re
import customtkinter as ctk
from tkinter import messagebox
from pytube import YouTube
import instaloader
from urllib.parse import urlparse
from threading import Thread

def download_video(video_url, save_path, progress_callback=None):
    try:
        with open(save_path, 'wb') as f:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            total_length = int(response.headers.get('content-length', 0))
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_length > 0:
                        progress_callback(100 * downloaded / total_length)
        # Show success message after successful download
        messagebox.showinfo("Success", f"Download completed successfully. Saved as {save_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading video: {e}")

def download_instagram_video(link, progress_callback=None):
    loader = instaloader.Instaloader()
    try:
        shortcode = link.split('/')[-2]
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        video_url = post.video_url
        download_video(video_url, "downloaded_instagram_video.mp4", progress_callback)
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading Instagram video: {e}")

def youtube_progress_callback(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = int((bytes_downloaded / total_size) * 100)
    update_progress(percentage)

def download_youtube_video(link, progress_callback=None):
    try:
        yt = YouTube(link)
        yt.register_on_progress_callback(youtube_progress_callback)
        stream = yt.streams.get_highest_resolution()
        stream.download(filename='youtube_video.mp4')
        # Show success message after successful download
        messagebox.showinfo("Success", "YouTube video downloaded successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading YouTube video: {e}")

def scrape_media(tweet_id):
    try:
        response = requests.get(f'https://api.vxtwitter.com/Twitter/status/{tweet_id}')
        response.raise_for_status()
        media_data = response.json()
        print("Scraped Media Data:", media_data)  # Debug: print the whole response
        return media_data.get('media_extended', [])
    except Exception as e:
        messagebox.showerror("Error", f"Failed to fetch media: {e}")
        return []

def download_media(tweet_id, progress_callback=None):
    tweet_media = scrape_media(tweet_id)
    if not tweet_media:
        messagebox.showerror("Error", "No media found for this tweet.")
        return

    print("Tweet Media for Download:", tweet_media)  # Check what we're trying to iterate over
    for media in tweet_media:
        if isinstance(media, dict) and 'url' in media:
            media_url = media['url']
            media_type = media.get('type', 'video')  # Default to 'video' if no type specified
            try:
                response = requests.get(media_url, stream=True)
                response.raise_for_status()
                file_extension = 'jpg' if media_type == 'image' else 'gif' if media_type == 'gif' else 'mp4'
                save_path = f'media.{file_extension}'
                total_length = int(response.headers.get('content-length', 0))
                downloaded = 0

                with open(save_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        if chunk:
                            file.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback and total_length > 0:
                                progress_callback(100 * downloaded / total_length)
                # Show success message after successful download
                messagebox.showinfo("Success", f"Media downloaded successfully. Saved as {save_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Error downloading media: {e}")
        else:
            print("Unexpected data type or structure in media:", type(media), media)
            messagebox.showerror("Error", "Unexpected media data structure. See console for details.")

def download_pinterest_image(link, progress_callback=None):
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        if image_tag and image_tag.get('content'):
            image_url = image_tag.get('content')
            download_video(image_url, "pinterest_image.jpg", progress_callback)
        else:
            messagebox.showerror("Error", "Image URL not found.")
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading Pinterest image: {e}")

operations = {
    'instagram.com': download_instagram_video,
    'youtube.com': download_youtube_video,
    'pinterest.com': download_pinterest_image,
    'twitter.com': lambda link, progress_callback=None: download_media(link.split('/')[-1], progress_callback)
}

def perform_operation(link):
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.lower().replace('www.', '')
    if domain in operations:
        operations[domain](link, update_progress)
    else:
        messagebox.showwarning("Unsupported URL", "The provided URL does not match any supported services.")

        
# Initialize CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Social Media Toolkit")
app.geometry("600x400")

progress_var = ctk.DoubleVar()
progress_bar = ctk.CTkProgressBar(app, variable=progress_var, width=300, height=20)
progress_bar.pack(pady=20)

entry = ctk.CTkEntry(app, width=400, placeholder_text="Enter a URL", height=35, corner_radius=10)
entry.pack(pady=20)

def update_progress(percent):
    progress_var.set(percent)
    app.update_idletasks()

def on_button_click():
    link = entry.get()
    Thread(target=perform_operation, args=(link,), daemon=True).start()

download_button = ctk.CTkButton(app, text="Analyze URL and Download", command=on_button_click, width=250, height=50, corner_radius=10, fg_color="#1a73e8", hover_color="#1557b2")
download_button.pack(pady=10)


def open_new_window():
    new_window = ctk.CTkToplevel(app)
    new_window.title("New Window")
    new_window.geometry("300x200")


download_list = ctk.CTkButton(app, text="Download multipul links",command=open_new_window, width=250, height=50, corner_radius=10, fg_color="#1a73e8", hover_color="#1557b2")
download_list.pack(pady=10)

app.mainloop()