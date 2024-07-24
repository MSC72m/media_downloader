from tkinter import messagebox
from bs4 import BeautifulSoup
import requests

from instagram import download_video
def download_pinterest_image(link):
    from oprations import random_save_path
    from oprations import on_operation_done
    try:
        save_path = random_save_path()
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        image_url = image_tag['content'] if image_tag else None
        if image_url:
            download_video(image_url, f"Pinterest_file{save_path}.jpg")
            messagebox.showinfo(
                "Success", "Pinterest image downloaded successfully.")
            on_operation_done()
        else:
            messagebox.showerror("Error", "Image URL not found.")
            on_operation_done()
    except Exception as e:
        messagebox.showerror(
            "Error", f"Error downloading Pinterest image: {e}")
        on_operation_done()




