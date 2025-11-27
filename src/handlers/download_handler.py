"""Concrete implementation of download handler."""

import re
import threading
import time
from pathlib import Path
from threading import Thread
from typing import Callable, List, Optional
from urllib.parse import urlparse

from src.core.config import AppConfig, get_config
from src.core.models import Download
from src.services.events.queue import Message
from src.services.youtube.downloader import YouTubeDownloader
from src.core.enums import ServiceType
from src.core.enums.message_level import MessageLevel
from src.core.models import Download, DownloadOptions, UIState
from src.core.base.base_handler import BaseHandler
from src.interfaces.service_interfaces import (
    IAutoCookieManager,
    ICookieHandler,
    IDownloadHandler,
    IDownloadService,
    IErrorHandler,
    IFileService,
    IMessageQueue,
    IServiceFactory,
    IUIState,
)
from src.services.events.queue import Message
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadHandler(BaseHandler, IDownloadHandler):
    """Download handler with proper dependency injection."""

    def __init__(
        self,
        download_service: IDownloadService,
        service_factory: IServiceFactory,
        file_service: IFileService,
        ui_state: IUIState,
        cookie_handler: ICookieHandler,
        auto_cookie_manager: Optional[IAutoCookieManager] = None,
        message_queue: Optional[IMessageQueue] = None,
        error_handler: Optional[IErrorHandler] = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(message_queue, config)
        self.download_service = download_service
        self.service_factory = service_factory
        self.file_service = file_service
        self.ui_state = ui_state
        self.cookie_handler = cookie_handler
        self.auto_cookie_manager = auto_cookie_manager
        self.error_handler = error_handler
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the download handler."""
        if self._initialized:
            return
        self._initialized = True

    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False

    def add_download(self, download: Download) -> None:
        """Add a download item."""
        self.download_service.add_download(download)

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        self.download_service.remove_downloads(indices)

    def clear_downloads(self) -> None:
        """Clear all download items."""
        self.download_service.clear_downloads()

    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        return self.download_service.get_downloads() or []

    def has_items(self) -> bool:
        """Check if there are any download items."""
        downloads = self.get_downloads()
        return len(downloads) > 0

    def start_downloads(
        self,
        downloads: List[Download],
        download_dir: Optional[str] = None,
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> None:
        """Start downloads by delegating to appropriate service handlers."""
        if download_dir is None:
            download_dir = str(self.config.paths.downloads_dir)
        logger.info(f"[DOWNLOAD_HANDLER] Starting {len(downloads)} downloads")

        # Early return: validate inputs
        if not downloads:
            logger.warning("[DOWNLOAD_HANDLER] No downloads provided")
            self._invoke_completion_callback(
                completion_callback, False, "No downloads to process"
            )
            return

        # Validate and expand download directory
        validated_dir = self._validate_download_directory(
            download_dir, completion_callback
        )
        if not validated_dir:
            return

        # Start downloads with concurrency control
        self._start_download_threads(
            downloads, validated_dir, progress_callback, completion_callback
        )

    def _download_worker(
        self,
        download: Download,
        download_dir: str,
        progress_callback,
        completion_callback,
    ):
        """Worker function to handle a single download."""
        logger.info(f"[DOWNLOAD_HANDLER] Worker started for: {download.name}")
        logger.info(f"[DOWNLOAD_HANDLER] URL: {download.url}")
        logger.info(f"[DOWNLOAD_HANDLER] Directory: {download_dir}")

        try:
            # Use injected service factory (mandatory dependency)
            logger.info(
                f"[DOWNLOAD_HANDLER] Using service factory: {self.service_factory}"
            )

            # Create a downloader with the download's specific options
            service_type = self.service_factory.detect_service_type(download.url)
            logger.info(f"[DOWNLOAD_HANDLER] Detected service type: {service_type}")

            # Debug: Log all download attributes
            logger.info(
                f"[DOWNLOAD_HANDLER] Download object attributes: {download.__dict__}"
            )
            logger.info(
                f"[DOWNLOAD_HANDLER] Has cookie_path: {hasattr(download, 'cookie_path')}"
            )
            if hasattr(download, "cookie_path"):
                logger.info(
                    f"[DOWNLOAD_HANDLER] cookie_path value: {download.cookie_path}"
                )

            downloader = self.service_factory.get_downloader(download.url)
            if not downloader:
                error_msg = f"No downloader available for URL: {download.url}"
                if self.error_handler:
                    self.error_handler.handle_service_failure("Download Handler", "downloader creation", error_msg, download.url)
                self._handle_download_failure(download, completion_callback, error_msg)
                return

            if service_type == ServiceType.YOUTUBE:
                cookie_manager = self.cookie_handler
                if cookie_manager and hasattr(download, "cookie_path") and download.cookie_path:
                    try:
                        cookie_manager.set_cookie_file(download.cookie_path)
                        logger.info("[DOWNLOAD_HANDLER] Successfully set cookies for download")
                    except Exception as e:
                        logger.error(f"[DOWNLOAD_HANDLER] Failed to set cookies: {e}")
                        if self.error_handler:
                            self.error_handler.handle_exception(e, "Setting cookies for download", "Download Handler")

            logger.info(
                f"[DOWNLOAD_HANDLER] Downloader obtained: {type(downloader).__name__}"
            )

            # Prepare download
            output_path = self._prepare_download_path(download, download_dir)
            progress_wrapper = self._create_progress_wrapper(
                download, progress_callback
            )

            # Execute download
            logger.info("[DOWNLOAD_HANDLER] Starting download...")
            success = downloader.download(
                url=download.url,
                save_path=output_path,
                progress_callback=progress_wrapper,
            )
            logger.info(
                f"[DOWNLOAD_HANDLER] Download completed with success: {success}"
            )

            # Handle result with early return
            if not success:
                self._handle_download_failure(
                    download,
                    completion_callback,
                    f"Failed to download: {download.name}",
                )
                return

            self._handle_download_success(download, completion_callback)
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logger.error(
                f"[DOWNLOAD_HANDLER] Download error for {download.name}: {e}",
                exc_info=True,
            )
            self._handle_download_failure(download, completion_callback, error_msg)


    def _validate_download_directory(
        self, download_dir: str, completion_callback
    ) -> Optional[str]:
        """Validate and expand download directory. Returns validated path or None."""
        try:
            expanded_dir = Path(download_dir).expanduser().resolve()

            if not expanded_dir.exists():
                expanded_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"[DOWNLOAD_HANDLER] Created directory: {expanded_dir}")
                return str(expanded_dir)

            if not expanded_dir.is_dir():
                logger.error(
                    f"[DOWNLOAD_HANDLER] Path is not a directory: {expanded_dir}"
                )
                self._invoke_completion_callback(
                    completion_callback,
                    False,
                    f"Invalid download directory: {download_dir}",
                )
                return None

            return str(expanded_dir)

        except Exception as e:
            logger.error(
                f"[DOWNLOAD_HANDLER] Invalid download directory: {download_dir}, error: {e}"
            )
            self._invoke_completion_callback(
                completion_callback,
                False,
                f"Invalid download directory: {download_dir}",
            )
            return None

    def _start_download_threads(
        self,
        downloads: List[Download],
        download_dir: str,
        progress_callback,
        completion_callback,
    ) -> None:
        """Start download threads with concurrency control."""
        max_concurrent = self.config.downloads.max_concurrent_downloads
        active_threads = []

        for download in downloads:
            # Skip invalid URLs
            if not download.url or not download.url.strip():
                logger.error(f"[DOWNLOAD_HANDLER] Invalid URL for: {download.name}")
                continue

            # Start download thread
            thread = threading.Thread(
                target=self._download_worker,
                args=(download, download_dir, progress_callback, completion_callback),
                daemon=True,
                name=f"DownloadWorker-{download.name[:20]}",
            )
            thread.start()
            active_threads.append(thread)

            # Concurrency control
            while len(active_threads) >= max_concurrent:
                active_threads = [t for t in active_threads if t.is_alive()]
                if len(active_threads) >= max_concurrent:
                    time.sleep(self.config.downloads.thread_sleep_interval)

    def _prepare_download_path(self, download: Download, download_dir: str) -> str:
        """Prepare and return the output path for download.

        Note: Returns path WITHOUT extension - the downloader will add the appropriate extension.
        """
        target_dir = Path(download_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"[DOWNLOAD_HANDLER] Sanitizing filename: {download.name}")

        # Use injected file service directly
        base_name = self.file_service.clean_filename(download.name or "download")
        # Don't add extension - downloader will add it
        output_path = str(target_dir / base_name)
        logger.info(
            f"[DOWNLOAD_HANDLER] Output path (without extension): {output_path}"
        )
        return output_path

    def _create_progress_wrapper(self, download: Download, progress_callback):
        """Create a progress wrapper function for the download."""
        if not progress_callback:
            return None

        def progress_wrapper(progress, speed):
            logger.info(
                f"[DOWNLOAD_HANDLER] Progress: {download.name} - {progress:.1f}% - {speed:.2f} bytes/s"
            )
            progress_callback(download, int(progress))

        return progress_wrapper

    def _handle_download_success(self, download: Download, completion_callback) -> None:
        """Handle successful download completion."""
        logger.info(f"[DOWNLOAD_HANDLER] Successfully downloaded: {download.name}")
        download.update_progress(100.0, 0.0)
        self._invoke_completion_callback(
            completion_callback, True, f"Downloaded: {download.name}"
        )

    def _handle_download_failure(
        self, download: Download, completion_callback, message: str
    ) -> None:
        """Handle download failure."""
        logger.error(f"[DOWNLOAD_HANDLER] {message}")
        download.mark_failed(message)
        if self.error_handler:
            self.error_handler.handle_service_failure("Download Handler", "download", message, download.url)
        self._invoke_completion_callback(completion_callback, False, message)

    def _invoke_completion_callback(
        self, callback, success: bool, message: str
    ) -> None:
        """Safely invoke completion callback if available."""
        if not callback:
            return

        callback(success, message)

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        return self.download_service.has_downloads()

    def get_options(self) -> DownloadOptions:
        """Get current download options."""
        default_dir = str(self.config.paths.downloads_dir)
        return DownloadOptions(
            save_directory=getattr(self.ui_state, "download_directory", default_dir)
        )

    def set_options(self, options: DownloadOptions) -> None:
        """Set download options."""
        self.ui_state.download_directory = options.save_directory

    # IDownloadHandler interface implementation
    def process_url(self, url: str, options: Optional[dict] = None) -> bool:
        """Process a URL for download."""
        try:
            # Create download from URL
            download = Download(
                url=url,
                name=self._extract_name_from_url(url),
                service_type=self._detect_service_type(url)
            )

            # Add to download service
            self.download_service.add_download(download)
            logger.info(f"[DOWNLOAD_HANDLER] Added download: {url}")
            return True

        except Exception as e:
            logger.error(f"[DOWNLOAD_HANDLER] Failed to process URL {url}: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Processing URL", "Download Handler")
            return False

    def handle_download_error(self, error: Exception) -> None:
        """Handle download errors."""
        logger.error(f"[DOWNLOAD_HANDLER] Download error: {error}", exc_info=True)
        
        if self.error_handler:
            self.error_handler.handle_exception(error, "Download operation", "Download Handler")
            return

        if self.message_queue:
            try:
                self.message_queue.add_message(
                    Message(
                        text=f"Download failed: {str(error)}",
                        level=MessageLevel.ERROR,
                        title="Download Error"
                    )
                )
            except Exception as msg_error:
                logger.error(f"[DOWNLOAD_HANDLER] Failed to show error message: {msg_error}")

    def is_available(self) -> bool:
        """Check if handler is available."""
        return self._initialized and self.download_service is not None

    def _extract_name_from_url(self, url: str) -> str:
        """Extract a default name from URL."""
        parsed = urlparse(url)
        return parsed.netloc or "download"

    def _detect_service_type(self, url: str) -> str:
        """Detect service type from URL."""
        url_lower = url.lower()
        
        for service_name, domains in self.config.network.service_domains.items():
            if any(domain in url_lower for domain in domains):
                return service_name
        return "unknown"
