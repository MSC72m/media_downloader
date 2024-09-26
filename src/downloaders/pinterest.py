from tkinter import messagebox
from bs4 import BeautifulSoup
import requests
import logging
import os

from src.utils.common import download_file, sanitize_filename

logger = logging.getLogger(__name__)


def download_pinterest_image(link, save_path):
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        image_url = image_tag['content'] if image_tag else None

        if image_url:
            sanitized_filename = sanitize_filename(f'{os.path.basename(save_path)}.jpg')
            full_save_path = os.path.join(os.path.dirname(save_path), sanitized_filename)
            if download_image(image_url, full_save_path):
                success_message = f"Pinterest image downloaded successfully as {full_save_path}"
                logger.info(success_message)
                messagebox.showinfo("Success", success_message)
                return True
            else:
                return False
        else:
            error_message = "Image URL not found."
            logger.error(error_message)
            messagebox.showerror("Error", error_message)
            return False
    except Exception as e:
        error_message = f"Error downloading Pinterest image: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)
        return False


def download_image(image_url, filename):
    return download_file(image_url, filename)
