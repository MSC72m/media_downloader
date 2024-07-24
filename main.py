
from tkinter import messagebox
from urllib.parse import urlparse
from twitter import download_twitter_media
from instagram import download_instagram_video, download_video
from youtube import download_youtube_video
from pintrest import download_pinterest_image

operations = {
    'instagram.com': download_instagram_video,
    'youtube.com': download_youtube_video,
    'pinterest.com': download_pinterest_image,
    'twitter.com': download_twitter_media,
    'x.com': download_twitter_media
}
from oprations import random_save_path

save_path = random_save_path()


def perform_operation(link):
    from oprations import on_operation_done
    parsed_url = urlparse(link)
    domain = parsed_url.netloc.lower().replace('www.', '')
    if domain in operations:
        operations[domain](link)
    else:
        messagebox.showwarning(
            "Unsupported URL", "The provided URL does not match any supported services.")
        on_operation_done()


from config import download_media_button

download_media_button.pack(pady=30)
download_media_button.place(x=100, y=150)

if __name__ == '__main__':
    from config import app

    app.mainloop()
