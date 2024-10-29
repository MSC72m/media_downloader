import os
import time
import requests
import logging
from typing import Optional, Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def download_file(
        url: str,
        filename: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
) -> bool:
    try:
        # Set up headers for more reliable downloads
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        response = requests.get(url, stream=True, headers=headers)
        response.raise_for_status()

        # Get file size
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0

        start_time = time.time()

        with open(filename, 'wb') as f:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                f.write(data)

                if progress_callback and total_size:
                    # Calculate progress percentage and speed
                    progress = (downloaded / total_size) * 100
                    elapsed_time = max(time.time() - start_time, 0.1)  # Avoid division by zero
                    speed = downloaded / elapsed_time
                    progress_callback(progress, speed)

        # Call one final time with 100% progress
        if progress_callback:
            progress_callback(100.0, 0.0)

        return True
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return False


def sanitize_filename(filename: str) -> str:
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')

    # Limit length
    max_length = 255
    name, ext = os.path.splitext(filename)
    if len(filename) > max_length:
        return name[:max_length - len(ext)] + ext

    return filename