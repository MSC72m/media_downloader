import requests
import re
from typing import Optional, List
from tkinter import messagebox

def extract_tweet_ids(text: str) -> Optional[List[str]]:
    """Extract tweet IDs from message."""
    unshortened_links = ''
    for link in re.findall(r"t\.co/[a-zA-Z0-9]+", text):
        try:
            unshortened_link = requests.get('https://' + link).url
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
            f'https://api.vxtwitter.com/Twitter/status/{tweet_id}', verify=False)
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


def download_media(tweet_media: List[dict], save_path) -> None:
    """Download media from the provided list of Twitter media dictionaries."""
    from main import save_path
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

            with open(f'Twitter_Media{save_path}.{file_extension}', 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            messagebox.showinfo(
                "Success", f"Media downloaded successfully. Saved as media.{file_extension}")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Error", f"Error downloading media: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {e}")

def download_twitter_media(link):
    tweet_ids = extract_tweet_ids(link)
    from oprations import on_operation_done
    from main import save_path
    if tweet_ids:
        for tweet_id in tweet_ids:
            media = scrape_media(int(tweet_id))
            if media:
                download_media(media, save_path)
                on_operation_done()
            else:
                messagebox.showerror("Error", "No media found for this tweet.")
                on_operation_done()
    else:
        messagebox.showerror("Error", "No supported tweet link found")
        on_operation_done()