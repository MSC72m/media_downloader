from tkinter import messagebox
from bs4 import BeautifulSoup
import requests
import logging

logger = logging.getLogger(__name__)


def download_pinterest_image(link, save_name):
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        image_url = image_tag['content'] if image_tag else None

        if image_url:
            filename = f"{save_name}.jpg"
            download_image(image_url, filename)
            success_message = f"Pinterest image downloaded successfully as Pinterest_file{filename}"
            logger.info(success_message)
            messagebox.showinfo("Success", success_message)
            return True
        else:
            error_message = "Image URL not found."
            logger.error(error_message)
            messagebox.showerror("Error", error_message)
    except Exception as e:
        error_message = f"Error downloading Pinterest image: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)


def download_image(image_url, filename):
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()

        with open(filename, 'wb') as file:
            for chunk in response.iter_content(8192):
                file.write(chunk)
        logger.info(f"Image downloaded and saved as {filename}")

    except requests.exceptions.RequestException as e:
        error_message = f"Error downloading image: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)
    except IOError as e:
        error_message = f"Error saving image: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)
