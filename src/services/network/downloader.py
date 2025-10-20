"""Network file downloader with progress tracking."""

import os
import time
from typing import Optional, Callable
import requests
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 10

def download_file(
    url: str,
    save_path: str,
    progress_callback: Optional[Callable[[float, float], None]] = None,
    chunk_size: int = 8192,
) -> bool:
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    session = requests.Session()
    temp_file = f"{save_path}.part"

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/91.0.4472.124 Safari/537.36"
            )
        }
        response = session.get(url, stream=True, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        file_size = int(response.headers.get("content-length", 0))
        downloaded = 0
        start_time = time.time()

        with open(temp_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                progress = (downloaded / file_size * 100) if file_size > 0 else -1
                elapsed = time.time() - start_time
                speed = downloaded / elapsed if elapsed > 0 else 0
                if progress_callback:
                    progress_to_report = progress if progress >= 0 else min(99, downloaded / (1024 * 1024))
                    progress_callback(progress_to_report, speed)

        os.replace(temp_file, save_path)
        if progress_callback:
            progress_callback(100, 0)
        logger.info("Download completed: %s", save_path)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Download error for %s: %s", url, e)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
    except Exception as e:
        logger.error("Unexpected error downloading %s: %s", url, e)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False


