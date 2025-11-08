"""Concrete implementation of download handler."""

from typing import Callable, List, Optional

from src.core.application.container import ServiceContainer
from src.core.models import Download, DownloadOptions
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadHandler:
    """Download handler using service container."""

    def __init__(self, container: ServiceContainer):
        self.container = container
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
        if download_service := self.container.get("download_service"):
            download_service.add_download(download)

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        if download_service := self.container.get("download_service"):
            download_service.remove_downloads(indices)

    def clear_downloads(self) -> None:
        """Clear all download items."""
        if download_service := self.container.get("download_service"):
            download_service.clear_downloads()

    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        if download_service := self.container.get("download_service"):
            if downloads := download_service.get_downloads():
                return downloads
        return []

    def has_items(self) -> bool:
        """Check if there are any download items."""
        downloads = self.get_downloads()
        return len(downloads) > 0

    def start_downloads(
        self,
        downloads: List[Download],
        download_dir: str = "~/Downloads",
        progress_callback: Optional[Callable[[Download, float], None]] = None,
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None,
    ) -> None:
        """Start downloads by delegating to appropriate service handlers."""
        logger.info(f"[DOWNLOAD_HANDLER] Starting {len(downloads)} downloads")

        for download in downloads:
            # Start each download in a separate thread
            import threading

            thread = threading.Thread(
                target=self._download_worker,
                args=(download, download_dir, progress_callback, completion_callback),
                daemon=True,
            )
            thread.start()

    def _download_worker(
        self,
        download: Download,
        download_dir: str,
        progress_callback,
        completion_callback,
    ):
        """Worker function to handle a single download by delegating to service factory with early returns."""
        logger.info(f"[DOWNLOAD_HANDLER] download_worker called for: {download.name}")
        logger.info(f"[DOWNLOAD_HANDLER] Download URL: {download.url}")
        logger.info(f"[DOWNLOAD_HANDLER] Download directory: {download_dir}")
        try:
            logger.info("[DOWNLOAD_HANDLER] Getting service_factory from container")
            service_factory = self.container.get("service_factory")
            if not service_factory:
                msg = "Service factory not available"
                logger.error(f"[DOWNLOAD_HANDLER] {msg}")
                if completion_callback:
                    completion_callback(False, msg)
                return
            logger.info(
                f"[DOWNLOAD_HANDLER] Service factory obtained: {service_factory}"
            )

            # Create a downloader with the download's specific options
            from src.core.models import ServiceType
            from src.services.youtube.downloader import YouTubeDownloader

            service_type = service_factory.detect_service_type(download.url)
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
            if hasattr(download, "selected_browser"):
                logger.info(
                    f"[DOWNLOAD_HANDLER] selected_browser value: {download.selected_browser}"
                )

            if service_type == ServiceType.YOUTUBE:
                # Get cookie manager and set cookies BEFORE creating downloader
                cookie_manager = service_factory.get_cookie_manager()

                logger.info(
                    f"[DOWNLOAD_HANDLER] Cookie manager available: {cookie_manager is not None}"
                )

                # Set cookies from download options
                if cookie_manager:
                    # Use cookie from download if specified
                    if hasattr(download, "cookie_path") and download.cookie_path:
                        logger.info(
                            f"[DOWNLOAD_HANDLER] Setting cookie from download: {download.cookie_path}"
                        )
                        try:
                            cookie_manager.set_youtube_cookies(download.cookie_path)
                            logger.info(
                                "[DOWNLOAD_HANDLER] Successfully set cookies for download"
                            )
                        except Exception as e:
                            logger.error(
                                f"[DOWNLOAD_HANDLER] Failed to set cookies: {e}"
                            )
                    elif (
                        hasattr(download, "selected_browser")
                        and download.selected_browser
                    ):
                        # Try to detect cookies from the selected browser
                        logger.info(
                            f"[DOWNLOAD_HANDLER] Detecting cookies from browser: {download.selected_browser}"
                        )
                        try:
                            from src.interfaces.cookie_detection import BrowserType

                            browser_map = {
                                "Chrome": BrowserType.CHROME,
                                "Firefox": BrowserType.FIREFOX,
                                "Safari": BrowserType.SAFARI,
                                "Edge": BrowserType.EDGE,
                            }
                            browser_type = browser_map.get(download.selected_browser)
                            if browser_type:
                                cookie_path = cookie_manager.detect_cookies_for_browser(
                                    browser_type
                                )
                                if cookie_path:
                                    logger.info(
                                        f"[DOWNLOAD_HANDLER] Detected cookies at: {cookie_path}"
                                    )
                                    # Cookies are automatically set in cookie_manager by detect_cookies_for_browser
                                else:
                                    logger.warning(
                                        f"[DOWNLOAD_HANDLER] Could not detect cookies for {download.selected_browser}"
                                    )
                            else:
                                logger.warning(
                                    f"[DOWNLOAD_HANDLER] Unknown browser type: {download.selected_browser}"
                                )
                        except Exception as e:
                            logger.error(
                                f"[DOWNLOAD_HANDLER] Failed to detect browser cookies: {e}"
                            )

                    # Verify cookies are set
                    has_cookies = cookie_manager.has_valid_cookies()
                    logger.info(
                        f"[DOWNLOAD_HANDLER] Cookie manager has valid cookies: {has_cookies}"
                    )
                    if has_cookies:
                        cookie_info = cookie_manager.get_youtube_cookie_info()
                        logger.info(
                            f"[DOWNLOAD_HANDLER] Cookie info for yt-dlp: {cookie_info}"
                        )

                # NOW create the downloader with the configured cookie_manager and browser
                downloader = YouTubeDownloader(
                    quality=getattr(download, "quality", "720p"),
                    download_playlist=getattr(download, "download_playlist", False),
                    audio_only=getattr(download, "audio_only", False),
                    cookie_manager=cookie_manager,
                    browser=getattr(download, "selected_browser", None),
                )
                logger.info(
                    f"[DOWNLOAD_HANDLER] Created YouTubeDownloader with quality={getattr(download, 'quality', '720p')}, audio_only={getattr(download, 'audio_only', False)}"
                )
            else:
                # Fallback to factory's default downloader
                downloader = service_factory.get_downloader(download.url)

            if not downloader:
                msg = f"No downloader available for URL: {download.url}"
                logger.error(f"[DOWNLOAD_HANDLER] {msg}")
                if completion_callback:
                    completion_callback(False, msg)
                return
            logger.info(
                f"[DOWNLOAD_HANDLER] Downloader obtained: {type(downloader).__name__}"
            )

            # Create output dir and sanitized filename via FileService
            from pathlib import Path

            logger.info("[DOWNLOAD_HANDLER] Getting file service")
            file_service = service_factory.get_file_service()
            logger.info(f"[DOWNLOAD_HANDLER] Creating target directory: {download_dir}")
            target_dir = Path(download_dir).expanduser()
            target_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[DOWNLOAD_HANDLER] Sanitizing filename: {download.name}")
            base_name = file_service.sanitize_filename(download.name or "download")
            ext = ".mp4"
            if getattr(download, "audio_only", False):
                ext = ".mp3"
            output_path = str(target_dir / f"{base_name}{ext}")
            logger.info(f"[DOWNLOAD_HANDLER] Output path: {output_path}")

            def progress_wrapper(progress, speed):
                logger.info(
                    f"[DOWNLOAD_HANDLER] Progress callback fired: {download.name} - {progress:.1f}% - {speed:.2f} bytes/s"
                )
                if progress_callback:
                    progress_callback(download, int(progress))

            logger.info("[DOWNLOAD_HANDLER] Starting download...")
            success = downloader.download(
                url=download.url,
                save_path=output_path,
                progress_callback=progress_wrapper,
            )
            logger.info(
                f"[DOWNLOAD_HANDLER] Download completed with success: {success}"
            )

            if not success:
                msg = f"Failed to download: {download.name}"
                logger.error(f"[DOWNLOAD_HANDLER] {msg}")
                if completion_callback:
                    completion_callback(False, msg)
                return

            logger.info(f"[DOWNLOAD_HANDLER] Successfully downloaded: {download.name}")
            if completion_callback:
                completion_callback(True, f"Downloaded: {download.name}")
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logger.error(
                f"[DOWNLOAD_HANDLER] Download error for {download.name}: {e}",
                exc_info=True,
            )
            if completion_callback:
                completion_callback(False, error_msg)

    def _handle_youtube_download(
        self,
        download: Download,
        download_dir: str,
        progress_callback,
        completion_callback,
    ):
        """Deprecated: unified through factory in _download_worker."""
        self._download_worker(
            download, download_dir, progress_callback, completion_callback
        )

    def _handle_twitter_download(
        self,
        download: Download,
        download_dir: str,
        progress_callback,
        completion_callback,
    ):
        """Deprecated: unified through factory in _download_worker."""
        self._download_worker(
            download, download_dir, progress_callback, completion_callback
        )

    def _handle_instagram_download(
        self,
        download: Download,
        download_dir: str,
        progress_callback,
        completion_callback,
    ):
        """Deprecated: unified through factory in _download_worker."""
        self._download_worker(
            download, download_dir, progress_callback, completion_callback
        )

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        if service_controller := self.container.get("service_controller"):
            if result := service_controller.has_active_downloads():
                return result
        return False

    def get_options(self) -> DownloadOptions:
        """Get current download options."""
        if ui_state := self.container.get("ui_state"):
            return DownloadOptions(
                save_directory=getattr(ui_state, "download_directory", "~/Downloads")
            )
        return DownloadOptions()

    def set_options(self, options: DownloadOptions) -> None:
        """Set download options."""
        if ui_state := self.container.get("ui_state"):
            ui_state.download_directory = options.save_directory
