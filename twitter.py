import requests
import re
from typing import Optional, List
from PyQt5.QtWidgets import QMessageBox
from operations import operations

def extract_tweet_ids(text: str) -> Optional[List[str]]:
    """Extract tweet IDs from message."""
    unshortened_links = ''
    for link in re.findall(r"t\.co/[a-zA-Z0-9]+", text):
        try:
            unshortened_link = requests.get('https://' + link, timeout=10).url
            unshortened_links += '\n' + unshortened_link
        except requests.exceptions.RequestException as e:
            print(f"Failed to unshorten link {link}: {e}")

    tweet_ids = re.findall(
        r"(?:twitter|x)\.com/.{1,15}/(?:web|status(?:es)?)/([0-9]{1,20})", text + unshortened_links)
    tweet_ids = list(dict.fromkeys(tweet_ids))
    return tweet_ids or None

def scrape_media(tweet_id: int) -> List[dict]:
    try:
        response = requests.get(
            f'https://api.vxtwitter.com/Twitter/status/{tweet_id}', verify=False, timeout=10)
        response.raise_for_status()
        media_data = response.json()
        print("Scraped Media Data:", media_data)
        return media_data.get('media_extended', [])
    except requests.exceptions.RequestException as e:
        QMessageBox.critical(None, "Error", f"Failed to fetch media: {str(e)}")
        return []
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Unexpected error: {str(e)}")
        return []

def download_media(tweet_media: List[dict], save_path) -> None:
    for media in tweet_media:
        media_url = media['url']
        try:
            response = requests.get(media_url, stream=True, verify=False, timeout=10)
            response.raise_for_status()

            if media['type'] == 'image':
                file_extension = 'jpg'
            elif media['type'] == 'gif':
                file_extension = 'gif'
            elif media['type'] == 'video':
                file_extension = 'mp4'
            else:
                continue

            with open(f'Twitter_Media{save_path}.{file_extension}', 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            QMessageBox.information(None, "Success", f"Media downloaded successfully. Saved as Twitter_Media{save_path}.{file_extension}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(None, "Error", f"Error downloading media: {str(e)}")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Unexpected error: {str(e)}")

def download_twitter_media(link, save_name, progress_callback):
    tweet_ids = extract_tweet_ids(link)
    save_path = operations.random_save_path()
    if tweet_ids:
        for i, tweet_id in enumerate(tweet_ids):
            media = scrape_media(int(tweet_id))
            if media:
                download_media(media, f"{save_path}_{i}")
                progress_callback.emit(100)  # Update progress
            else:
                QMessageBox.warning(None, "Warning", f"No media found for tweet ID: {tweet_id}")
        operations.on_operation_done()
    else:
        QMessageBox.critical(None, "Error", "No supported tweet link found")
        operations.on_operation_done()