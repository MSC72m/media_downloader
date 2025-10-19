"""Concrete implementation of download handler."""

import logging
from typing import List, Callable, Optional
from src.core.models import Download, DownloadOptions
from src.core.container import ServiceContainer

logger = logging.getLogger(__name__)


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
        download_service = self.container.get('download_service')
        if download_service:
            download_service.add_download(download)

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove download items by indices."""
        download_service = self.container.get('download_service')
        if download_service:
            download_service.remove_downloads(indices)

    def clear_downloads(self) -> None:
        """Clear all download items."""
        download_service = self.container.get('download_service')
        if download_service:
            download_service.clear_downloads()

    def get_downloads(self) -> List[Download]:
        """Get all download items."""
        download_service = self.container.get('download_service')
        if download_service:
            return download_service.get_downloads()
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
        completion_callback: Optional[Callable[[bool, Optional[str]], None]] = None
    ) -> None:
        """Start downloads by delegating to appropriate service handlers."""
        logger.info(f"[DOWNLOAD_HANDLER] Starting {len(downloads)} downloads")
        
        for download in downloads:
            # Start each download in a separate thread
            import threading
            thread = threading.Thread(
                target=self._download_worker,
                args=(download, download_dir, progress_callback, completion_callback),
                daemon=True
            )
            thread.start()

    def _download_worker(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Worker function to handle a single download by delegating to appropriate service."""
        logger.info(f"[DOWNLOAD_HANDLER] download_worker called for: {download.name}")
        try:
            # Determine service type and delegate to appropriate service
            service_type = getattr(download, 'service_type', 'youtube')
            
            if service_type == 'youtube':
                self._handle_youtube_download(download, download_dir, progress_callback, completion_callback)
            elif service_type == 'twitter':
                self._handle_twitter_download(download, download_dir, progress_callback, completion_callback)
            elif service_type == 'instagram':
                self._handle_instagram_download(download, download_dir, progress_callback, completion_callback)
            else:
                error_msg = f"Unsupported service type: {service_type}"
                logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)
                    
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logger.error(f"[DOWNLOAD_HANDLER] Download error for {download.name}: {e}")
            if completion_callback:
                completion_callback(False, error_msg)

    def _handle_youtube_download(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Handle YouTube downloads using the YouTube service."""
        try:
            from src.services.youtube.downloader import YouTubeDownloader
            
            # Create sanitized directory name
            import re
            from pathlib import Path
            sanitized_name = re.sub(r'[^\w\s-]', '', download.name).strip()
            sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name)
            video_dir = Path(download_dir).expanduser() / sanitized_name
            video_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[DOWNLOAD_HANDLER] Created video directory: {video_dir}")

            # Get cookie manager from container
            cookie_manager = self.container.get('cookie_manager')

            # Create YouTube downloader with appropriate settings
            youtube_downloader = YouTubeDownloader(
                quality=getattr(download, 'quality', '720p'),
                download_playlist=getattr(download, 'download_playlist', False),
                audio_only=getattr(download, 'audio_only', False),
                cookie_manager=cookie_manager
            )

            # Create output path
            output_path = video_dir / f"{download.name}.mp4"
            if getattr(download, 'audio_only', False):
                output_path = video_dir / f"{download.name}.mp3"

            # Progress callback wrapper
            def progress_wrapper(progress, speed):
                if progress_callback:
                    progress_callback(download, int(progress))

            # Perform download
            success = youtube_downloader.download(
                url=download.url,
                save_path=str(output_path),
                progress_callback=progress_wrapper
            )

            if success:
                logger.info(f"[DOWNLOAD_HANDLER] Successfully downloaded: {download.name}")
                if completion_callback:
                    completion_callback(True, f"Downloaded: {download.name}")
            else:
                error_msg = f"Failed to download: {download.name}"
                logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)

        except Exception as e:
            error_msg = f"YouTube download error: {str(e)}"
            logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
            if completion_callback:
                completion_callback(False, error_msg)

    def _handle_twitter_download(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Handle Twitter downloads using the Twitter service."""
        try:
            from src.services.twitter.downloader import TwitterDownloader
            
            # Create sanitized directory name
            import re
            from pathlib import Path
            sanitized_name = re.sub(r'[^\w\s-]', '', download.name).strip()
            sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name)
            video_dir = Path(download_dir).expanduser() / sanitized_name
            video_dir.mkdir(parents=True, exist_ok=True)

            # Create Twitter downloader
            twitter_downloader = TwitterDownloader()
            
            # Create output path
            output_path = video_dir / f"{download.name}.mp4"

            # Perform download
            success = twitter_downloader.download(
                url=download.url,
                save_path=str(output_path),
                progress_callback=progress_callback
            )

            if success:
                logger.info(f"[DOWNLOAD_HANDLER] Successfully downloaded: {download.name}")
                if completion_callback:
                    completion_callback(True, f"Downloaded: {download.name}")
            else:
                error_msg = f"Failed to download: {download.name}"
                logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)

        except Exception as e:
            error_msg = f"Twitter download error: {str(e)}"
            logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
            if completion_callback:
                completion_callback(False, error_msg)

    def _handle_instagram_download(self, download: Download, download_dir: str, progress_callback, completion_callback):
        """Handle Instagram downloads using the Instagram service."""
        try:
            from src.services.instagram.downloader import InstagramDownloader
            
            # Create sanitized directory name
            import re
            from pathlib import Path
            sanitized_name = re.sub(r'[^\w\s-]', '', download.name).strip()
            sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name)
            video_dir = Path(download_dir).expanduser() / sanitized_name
            video_dir.mkdir(parents=True, exist_ok=True)

            # Create Instagram downloader
            instagram_downloader = InstagramDownloader()
            
            # Create output path
            output_path = video_dir / f"{download.name}.mp4"

            # Perform download
            success = instagram_downloader.download(
                url=download.url,
                save_path=str(output_path),
                progress_callback=progress_callback
            )

            if success:
                logger.info(f"[DOWNLOAD_HANDLER] Successfully downloaded: {download.name}")
                if completion_callback:
                    completion_callback(True, f"Downloaded: {download.name}")
            else:
                error_msg = f"Failed to download: {download.name}"
                logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
                if completion_callback:
                    completion_callback(False, error_msg)

        except Exception as e:
            error_msg = f"Instagram download error: {str(e)}"
            logger.error(f"[DOWNLOAD_HANDLER] {error_msg}")
            if completion_callback:
                completion_callback(False, error_msg)

    def has_active_downloads(self) -> bool:
        """Check if there are active downloads."""
        service_controller = self.container.get('service_controller')
        if service_controller:
            return service_controller.has_active_downloads()
        return False

    def get_options(self) -> DownloadOptions:
        """Get current download options."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            return DownloadOptions(
                save_directory=getattr(ui_state, 'download_directory', '~/Downloads')
            )
        return DownloadOptions()

    def set_options(self, options: DownloadOptions) -> None:
        """Set download options."""
        ui_state = self.container.get('ui_state')
        if ui_state:
            ui_state.download_directory = options.save_directory