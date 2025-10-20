import os
import requests
from typing import Callable, Optional
import time
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Constants
DEFAULT_TIMEOUT = 10  # seconds
MAX_RETRIES = 3

def download_file(
    url: str,
    save_path: str,
    progress_callback: Optional[Callable[[float, float], None]] = None,
    chunk_size: int = 8192
) -> bool:
    """
    Download a file with progress monitoring.

    Args:
        url: URL to download from
        save_path: Path to save the file to
        progress_callback: Callback for progress updates
        chunk_size: Size of chunks to download

    Returns:
        True if download was successful, False otherwise
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    # Extract the domain from the URL to check connectivity
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    site_name = None

    for name, service_url in SERVICE_URLS.items():
        if domain in service_url:
            site_name = name
            break

    if site_name:
        connected, error_msg = check_site_connection(site_name)
        if not connected:
            logger.error(f"Download failed: {error_msg}")
            return False

    # Setup session with retries
    session = requests.Session()
    temp_file = f"{save_path}.part"

    try:
        # Make a streaming request with simple custom headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = session.get(url, stream=True, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        # Get file size if available
        file_size = int(response.headers.get('content-length', 0))

        # Progress tracking
        downloaded = 0
        start_time = time.time()

        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Calculate progress and speed
                    progress = (downloaded / file_size * 100) if file_size > 0 else -1
                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0

                    if progress_callback:
                        # If file size unknown, report indeterminate progress
                        progress_to_report = progress if progress >= 0 else min(99, downloaded / (1024 * 1024))
                        progress_callback(progress_to_report, speed)

        # Rename temp file to final filename
        os.replace(temp_file, save_path)

        if progress_callback:
            progress_callback(100, 0)  # Final progress update

        logger.info(f"Download completed: {save_path} ({downloaded/1024/1024:.2f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Download error for {url}: {str(e)}")
        # Clean up failed download
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading {url}: {str(e)}")
        # Clean up failed download
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
