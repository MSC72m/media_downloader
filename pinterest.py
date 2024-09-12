from tkinter import messagebox
from bs4 import BeautifulSoup
import requests

def download_pinterest_image(link, save_name):
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        image_url = image_tag['content'] if image_tag else None

        if image_url:
            download_image(image_url, f"{save_name}.jpg")
            messagebox.showinfo("Success", f"Pinterest image downloaded successfully as Pinterest_file{save_name}.jpg")
        else:
            messagebox.showerror("Error", "Image URL not found.")
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading Pinterest image: {str(e)}")

def download_image(image_url, filename):
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()

        with open(filename, 'wb') as file:
            for chunk in response.iter_content(8192):
                file.write(chunk)

    except requests.exceptions.RequestException as e:
        messagebox.showerror("Error", f"Error downloading image: {str(e)}")
    except IOError as e:
        messagebox.showerror("Error", f"Error saving image: {str(e)}")