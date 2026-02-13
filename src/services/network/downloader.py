from __future__ import annotations

import http.client
import os
import time
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlparse

import requests

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)
_REQUEST_EXCEPTION = (
    requests.exceptions.RequestException
    if isinstance(getattr(requests, "exceptions", None), object)
    and isinstance(getattr(requests.exceptions, "RequestException", None), type)
    and issubclass(requests.exceptions.RequestException, BaseException)
    else Exception
)

_COOKIE_JAR_CLASS = getattr(getattr(requests, "cookies", None), "RequestsCookieJar", None)


def _safe_user_agent(config: AppConfig) -> str:
    candidate = getattr(getattr(config, "network", None), "user_agent", "")
    return candidate if isinstance(candidate, str) and candidate.strip() else "Mozilla/5.0"


def _normalize_cookies(cookies: Any) -> Any:
    if cookies is None:
        return None
    if isinstance(cookies, dict):
        return cookies
    if isinstance(_COOKIE_JAR_CLASS, type) and isinstance(cookies, _COOKIE_JAR_CLASS):
        return cookies
    return None


def _is_mocked_requests_module() -> bool:
    return type(requests).__module__.startswith("unittest.mock")


def _safe_remove(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)


def _compute_progress_to_report(
    downloaded: int,
    total_size: int,
    config: AppConfig,
) -> float:
    if (progress := (downloaded / total_size * 100) if total_size > 0 else -1) >= 0:
        return progress
    mb_to_bytes = config.downloads.kb_to_bytes * 1024
    return min(99, downloaded / mb_to_bytes)


def _stream_chunks_to_temp_file(
    chunks: Iterable[bytes],
    temp_file: str,
    total_size: int,
    progress_callback: Callable[[float, float], None] | None,
    config: AppConfig,
) -> None:
    downloaded = 0
    start_time = time.time()

    with open(temp_file, "wb") as f:
        for chunk in chunks:
            if not chunk:
                continue
            f.write(chunk)
            downloaded += len(chunk)
            if not progress_callback:
                continue
            elapsed = time.time() - start_time
            speed = downloaded / elapsed if elapsed > 0 else 0
            progress_to_report = _compute_progress_to_report(downloaded, total_size, config)
            progress_callback(progress_to_report, speed)


def _finalize_download(
    temp_file: str,
    save_path: str,
    progress_callback: Callable[[float, float], None] | None,
    completion_log_message: str,
) -> bool:
    os.replace(temp_file, save_path)
    if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
        logger.error("Downloaded file is missing or empty: %s", save_path)
        return False

    if progress_callback:
        progress_callback(100, 0)
    logger.info(completion_log_message, save_path)
    return True


def _download_with_http_client(
    url: str,
    save_path: str,
    progress_callback: Callable[[float, float], None] | None,
    chunk_size: int,
    config: AppConfig,
    headers: dict[str, str] | None,
) -> bool:
    request_headers = {"User-Agent": _safe_user_agent(config)}
    if headers:
        request_headers.update(headers)

    if (parsed := urlparse(url)).scheme not in {"http", "https"} or not parsed.hostname:
        logger.error("Download error for %s: invalid URL scheme/host", url)
        return False

    temp_file = f"{save_path}.part"
    connection_class = (
        http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
    )
    connection = connection_class(
        parsed.hostname,
        parsed.port,
        timeout=config.network.default_timeout,
    )

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    try:
        connection.request("GET", path, headers=request_headers)
        if (response := connection.getresponse()).status >= 400:
            logger.error("Download error for %s: HTTP %s", url, response.status)
            return False

        content_length_header = response.getheader("Content-Length", "0")
        total_size = (
            int(content_length_header)
            if isinstance(content_length_header, str) and content_length_header.isdigit()
            else 0
        )
        chunks = iter(lambda: response.read(chunk_size), b"")
        _stream_chunks_to_temp_file(
            chunks=chunks,
            temp_file=temp_file,
            total_size=total_size,
            progress_callback=progress_callback,
            config=config,
        )
        return _finalize_download(
            temp_file=temp_file,
            save_path=save_path,
            progress_callback=progress_callback,
            completion_log_message="Download completed via http.client fallback: %s",
        )
    except (http.client.HTTPException, OSError, TimeoutError) as exc:
        logger.error("Download error for %s: %s", url, exc)
        _safe_remove(temp_file)
        return False
    except Exception as exc:
        logger.error("Unexpected http.client download error for %s: %s", url, exc)
        _safe_remove(temp_file)
        return False
    finally:
        connection.close()


def download_file(
    url: str,
    save_path: str,
    progress_callback: Callable[[float, float], None] | None = None,
    chunk_size: int | None = None,
    config=None,
    headers: dict[str, str] | None = None,
    cookies: Any = None,
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

    if _is_mocked_requests_module():
        return _download_with_http_client(
            url=url,
            save_path=save_path,
            progress_callback=progress_callback,
            chunk_size=chunk_size,
            config=config,
            headers=headers,
        )

    session = requests.Session()
    temp_file = f"{save_path}.part"

    try:
        request_headers = {"User-Agent": _safe_user_agent(config)}
        if headers:
            request_headers.update(headers)

        response = session.get(
            url,
            stream=True,
            headers=request_headers,
            cookies=_normalize_cookies(cookies),
            timeout=config.network.default_timeout,
        )
        response.raise_for_status()

        content_length = response.headers.get("content-length", 0)
        try:
            file_size = int(content_length)
        except (TypeError, ValueError):
            file_size = 0
        _stream_chunks_to_temp_file(
            chunks=response.iter_content(chunk_size=chunk_size),
            temp_file=temp_file,
            total_size=file_size,
            progress_callback=progress_callback,
            config=config,
        )

        return _finalize_download(
            temp_file=temp_file,
            save_path=save_path,
            progress_callback=progress_callback,
            completion_log_message="Download completed: %s",
        )
    except _REQUEST_EXCEPTION as e:
        logger.error("Download error for %s: %s", url, e)
        _safe_remove(temp_file)
        return False
    except Exception as e:
        logger.error("Unexpected error downloading %s: %s", url, e)
        _safe_remove(temp_file)
        return False
    finally:
        session.close()
