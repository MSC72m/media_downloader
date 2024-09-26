import requests
import re
from typing import Optional, List
from tkinter import messagebox
import logging
import os

from src.utils.common import download_file, sanitize_filename

logger = logging.getLogger(__name__)


def extract_tweet_ids(text: str) -> Optional[List[str]]:
    unshortened_links = ''
    for link in re.findall(r"t\.co/[a-zA-Z0-9]+", text):
        try:
            unshortened_link = requests.get('https://' + link, timeout=10).url
            unshortened_links += '\n' + unshortened_link
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to unshorten link {link}: {e}")

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
        logger.info(f"Scraped Media Data for tweet {tweet_id}: {media_data}")
        return media_data.get('media_extended', [])
    except requests.exceptions.RequestException as e:
        error_message = f"Failed to fetch media: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)
        return []
    except Exception as e:
        error_message = f"Unexpected error: {str(e)}"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)
        return []


def download_media(tweet_media: List[dict], save_path) -> bool:
    for media in tweet_media:
        media_url = media['url']
        try:
            if media['type'] == 'image':
                file_extension = '.jpg'
            elif media['type'] == 'gif':
                file_extension = '.gif'
            elif media['type'] == 'video':
                file_extension = '.mp4'
            else:
                logger.warning(f"Unsupported media type: {media['type']}")
                continue

            filename = sanitize_filename(f'{os.path.basename(save_path)}{file_extension}')
            full_save_path = os.path.join(os.path.dirname(save_path), filename)
            if download_file(media_url, full_save_path, is_twitter=True):
                return True
            else:
                return False
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            logger.error(error_message)
            messagebox.showerror("Error", error_message)
            return False


def download_twitter_media(link, save_path):
    tweet_ids = extract_tweet_ids(link)
    if tweet_ids:
        for i, tweet_id in enumerate(tweet_ids):
            logger.info(f"Attempting to download media for tweet ID: {tweet_id}")
            media = scrape_media(int(tweet_id))
            if media:
                download_media(media, f"{save_path}_{i}")
                return True
            else:
                warning_message = f"No media found for tweet ID: {tweet_id}"
                logger.warning(warning_message)
                messagebox.showwarning("Warning", warning_message)
                return False
    else:
        error_message = "No supported tweet link found"
        logger.error(error_message)
        messagebox.showerror("Error", error_message)
        return False
