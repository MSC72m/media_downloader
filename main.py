import requests
from bs4 import BeautifulSoup
import re
import customtkinter as ctk
from tkinter import messagebox
from pytube import YouTube
import instaloader
from urllib.parse import urlparse
from typing import Optional, List
from threading import Thread

def download_instagram_video(link):
    loader = instaloader.Instaloader()
    try:
        post = instaloader.Post.from_shortcode(loader.context, link.split('/')[-2])
        video_url = post.video_url
        download_video(video_url, "downloaded_instagram_video.mp4")
        messagebox.showinfo("Success", "Video downloaded successfully.")
        on_operation_done()  # Callback to re-enable the button
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading Instagram video: {e}")
        on_operation_done()  # Callback to re-enable the button

def download_video(video_url, save_path):
    try:
        with open(save_path, 'wb') as f:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Error downloading video: {e}")
    except IOError as e:
        messagebox.showerror("Error", f"Error saving video: {e}")

def extract_tweet_ids(text: str) -> Optional[List[str]]:
    """Extract tweet IDs from message."""
    unshortened_links = ''
    for link in re.findall(r"t\.co/[a-zA-Z0-9]+", text):
        try:
            unshortened_link = requests.get('https://' + link).url
            unshortened_links += '\n' + unshortened_link
        except requests.exceptions.RequestException as e:
            print(f"Failed to unshorten link {link}: {e}")

    tweet_ids = re.findall(r"(?:twitter|x)\.com/.{1,15}/(?:web|status(?:es)?)/([0-9]{1,20})", text + unshortened_links)
    tweet_ids = list(dict.fromkeys(tweet_ids))
    return tweet_ids or None

def scrape_media(tweet_id: int) -> List[dict]:
    try:
        response = requests.get(f'https://api.vxtwitter.com/Twitter/status/{tweet_id}', verify=False)
        response.raise_for_status()
        media_data = response.json()
        print("Scraped Media Data:", media_data)
        return media_data.get('media_extended', [])
    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Failed to fetch media: {e}")
        return []
    except Exception as e:
        messagebox.showerror("Error", f"Unexpected error: {e}")
        return []

def download_media(tweet_media: List[dict]) -> None:
    """Download media from the provided list of Twitter media dictionaries."""
    for media in tweet_media:
        media_url = media['url']
        try:
            response = requests.get(media_url, stream=True, verify=False)
            response.raise_for_status()

            if media['type'] == 'image':
                file_extension = 'jpg'
            elif media['type'] == 'gif':
                file_extension = 'gif'
            elif media['type'] == 'video':
                file_extension = 'mp4'
            else:
                continue

            with open(f'media.{file_extension}', 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            messagebox.showinfo("Success", f"Media downloaded successfully. Saved as media.{file_extension}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Error downloading media: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")

def download_youtube_video(link):
    try:
        yt = YouTube(link)
        stream = yt.streams.get_highest_resolution()
        stream.download(filename='youtube_video.mp4')
        messagebox.showinfo("Success", "YouTube video downloaded successfully.")
        on_operation_done()  # Callback to re-enable the button
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading YouTube video: {e}")
        on_operation_done()  # Callback to re-enable the button

def download_pinterest_image(link):
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        image_url = image_tag['content'] if image_tag else None
        if image_url:
            download_video(image_url, "pinterest_image.jpg")
            messagebox.showinfo("Success", "Pinterest image downloaded successfully.")
            on_operation_done()  # Callback to re-enable the button
        else:
            messagebox.showerror("Error", "Image URL not found.")
            on_operation_done()  # Callback to re-enable the button
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading Pinterest image: {e}")
        on_operation_done()  # Callback to re-enable the button

def download_twitter_media(link):
    tweet_ids = extract_tweet_ids(link)
    if tweet_ids:
        for tweet_id in tweet_ids:
            media = scrape_media(int(tweet_id))
            if media:
                download_media(media)
                on_operation_done()  # Callback to re-enable the button after each media download
            else:
                messagebox.showerror("Error", "No media found for this tweet.")
                on_operation_done()  # Callback to re-enable the button if no media found
    else:
        messagebox.showerror("Error", "No supported tweet link found")
        on_operation_done()  # Callback to re-enable the button if no tweet IDs found

operations = {
    'instagram.com': download_instagram_video,
    'youtube.com': download_youtube_video,
    'pinterest.com': download_pinterest_image,
    'twitter.com': download_twitter_media,
    'x.com': download_twitter_media
}

def perform_operation(link):
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.lower().replace('www.', '')
    if domain in operations:
        operations[domain](link)
    else:
        messagebox.showwarning("Unsupported URL", "The provided URL does not match any supported services.")
        on_operation_done()  # Callback to re-enable the button if URL is unsupported

app = ctk.CTk()
app.title("Social Media Toolkit")
app.geometry("500x500")

entry = ctk.CTkEntry(app, width=430, placeholder_text="Enter a URL", height=45, corner_radius=30)
entry.pack(pady=65)

def on_button_click():
    link = entry.get()
    download_media_button.configure(state=ctk.DISABLED)  # Disable the button
    Thread(target=perform_operation, args=(link,), daemon=True).start()

def on_operation_done():
    download_media_button.configure(state=ctk.NORMAL)

download_media_button = ctk.CTkButton(app, text="Analyze URL and Download", command=on_button_click, width=300,
                                      height=60, corner_radius=50, fg_color="#1a73e8", hover_color="#1557b2")
download_media_button.pack(pady=30)
download_media_button.place(x=100, y=150)

app.mainloop()
