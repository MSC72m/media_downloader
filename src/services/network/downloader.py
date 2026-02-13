from __future__ import annotations

import os
import time
from collections.abc import Callable

import requests

from src.core.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)
_REQUEST_EXCEPTION = (
    requests.exceptions.RequestException
    if isinstance(getattr(requests, "exceptions", None), object)
    and isinstance(getattr(requests.exceptions, "RequestException", None), type)
    and issubclass(requests.exceptions.RequestException, BaseException)
    else Exception
)


def download_file(  # noqa: PLR0912
    url: str,
    save_path: str,
    progress_callback: Callable[[float, float], None] | None = None,
    chunk_size: int | None = None,
    config=None,
    headers: dict[str, str] | None = None,
    cookies: requests.cookies.RequestsCookieJar | dict[str, str] | None = None,
) -> bool:
    """Download a file from URL.

    Args:
        url: URL to download from
        save_path: Path to save the file
        progress_callback: Optional callback for progress updates
        chunk_size: Chunk size in bytes (uses config if not provided)
        config: AppConfig instance (defaults to get_config() if None)
    """
    if config is None:
        config = get_config()

    if chunk_size is None:
        chunk_size = config.downloads.chunk_size

    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)

    session = requests.Session()
    temp_file = f"{save_path}.part"

    try:
        request_headers = {"User-Agent": config.network.user_agent}
        if headers:
            request_headers.update(headers)

        response = session.get(
            url,
            stream=True,
            headers=request_headers,
            cookies=cookies,
            timeout=config.network.default_timeout,
        )
        response.raise_for_status()

        content_length = response.headers.get("content-length", 0)
        try:
            file_size = int(content_length)
        except (TypeError, ValueError):
            file_size = 0
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
                    mb_to_bytes = config.downloads.kb_to_bytes * 1024
                    progress_to_report = (
                        progress if progress >= 0 else min(99, downloaded / mb_to_bytes)
                    )
                    progress_callback(progress_to_report, speed)

        os.replace(temp_file, save_path)
        if not os.path.exists(save_path):
            logger.error("Download moved file but target is missing: %s", save_path)
            return False
        if os.path.getsize(save_path) == 0:
            logger.error("Downloaded file is empty: %s", save_path)
            return False

        if progress_callback:
            progress_callback(100, 0)
        logger.info("Download completed: %s", save_path)
        return True
    except _REQUEST_EXCEPTION as e:
        logger.error("Download error for %s: %s", url, e)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
    except Exception as e:
        logger.error("Unexpected error downloading %s: %s", url, e)
        if os.path.exists(temp_file):
            os.remove(temp_file)
        return False
    finally:
        session.close()
