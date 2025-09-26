"""HTTP file downloader service."""

import os
import time
import logging
from typing import Optional, Callable
import requests

from .models import DownloadResult
from ...interfaces.cookie_detection import ServiceType

logger = logging.getLogger(__name__)


class FileDownloader:
    """HTTP-based file downloader with progress monitoring."""

    DEFAULT_TIMEOUT = 10  # seconds
    DEFAULT_CHUNK_SIZE = 8192

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.network_service = None

    def set_network_service(self, network_service):
        """Set network service for connectivity checks."""
        self.network_service = network_service

    def download_file(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> DownloadResult:
        """
        Download a file with progress monitoring.

        Args:
            url: URL to download from
            save_path: Path to save the file to
            progress_callback: Callback for progress updates (progress, speed)

        Returns:
            DownloadResult with operation details
        """
        start_time = time.time()

        # Ensure directory exists
        try:
            os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        except Exception as e:
            return DownloadResult(
                success=False,
                error_message=f"Failed to create directory: {str(e)}",
                download_time=time.time() - start_time
            )

        # Check connectivity if network service is available
        if self.network_service:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc

                # Try to match domain to service type
                service_type = self._domain_to_service_type(domain)
                if service_type and hasattr(self.network_service, 'is_service_connected'):
                    if not self.network_service.is_service_connected(service_type):
                        return DownloadResult(
                            success=False,
                            error_message=f"Cannot connect to {service_type}",
                            download_time=time.time() - start_time
                        )
            except Exception:
                # If connectivity check fails, continue with download attempt
                pass

        # Setup session with retries
        session = requests.Session()
        temp_file = f"{save_path}.part"

        try:
            # Make a streaming request with simple custom headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            response = session.get(url, stream=True, headers=headers, timeout=self.timeout)
            response.raise_for_status()

            # Get file size if available
            file_size = int(response.headers.get('content-length', 0))

            # Progress tracking
            downloaded = 0
            download_start = time.time()

            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:  # filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Calculate progress and speed
                        progress = (downloaded / file_size * 100) if file_size > 0 else -1
                        elapsed = time.time() - download_start
                        speed = downloaded / elapsed if elapsed > 0 else 0

                        if progress_callback:
                            # If file size unknown, report indeterminate progress
                            progress_to_report = progress if progress >= 0 else min(99, downloaded / (1024 * 1024))
                            progress_callback(progress_to_report, speed)

            # Rename temp file to final filename
            os.replace(temp_file, save_path)

            if progress_callback:
                progress_callback(100, 0)  # Final progress update

            download_time = time.time() - start_time
            logger.info(f"Download completed: {save_path} ({downloaded/1024/1024:.2f} MB in {download_time:.2f}s)")

            return DownloadResult(
                success=True,
                file_path=save_path,
                bytes_downloaded=downloaded,
                download_time=download_time
            )

        except requests.exceptions.RequestException as e:
            download_time = time.time() - start_time
            logger.error(f"Download error for {url}: {str(e)}")
            # Clean up failed download
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return DownloadResult(
                success=False,
                error_message=str(e),
                download_time=download_time
            )
        except Exception as e:
            download_time = time.time() - start_time
            logger.error(f"Unexpected error downloading {url}: {str(e)}")
            # Clean up failed download
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return DownloadResult(
                success=False,
                error_message=str(e),
                download_time=download_time
            )

    def _domain_to_service_type(self, domain: str) -> Optional[ServiceType]:
        """Convert domain to ServiceType."""
        domain = domain.lower()

        for service_type in ServiceType:
            if service_type.value.lower() in domain:
                return service_type

        return None