from PyQt5.QtWidgets import QMessageBox
from bs4 import BeautifulSoup
import requests
from operations import operations

def download_pinterest_image(link, save_name, progress_callback):
    try:
        response = requests.get(link, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        image_tag = soup.find('meta', property='og:image')
        image_url = image_tag['content'] if image_tag else None

        if image_url:
            save_path = operations.random_save_path()
            download_image(image_url, f"Pinterest_file{save_path}.jpg")
            progress_callback.emit(100)  # Update progress
            QMessageBox.information(None, "Success", f"Pinterest image downloaded successfully as Pinterest_file{save_path}.jpg")
        else:
            QMessageBox.critical(None, "Error", "Image URL not found.")
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Error downloading Pinterest image: {str(e)}")
    finally:
        operations.on_operation_done()

def download_image(image_url, filename):
    try:
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()

        with open(filename, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)

    except requests.exceptions.RequestException as e:
        QMessageBox.critical(None, "Error", f"Error downloading image: {str(e)}")
    except IOError as e:
        QMessageBox.critical(None, "Error", f"Error saving image: {str(e)}")