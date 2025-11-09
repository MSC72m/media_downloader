"""YouTube link handler implementation."""

import re
from src.utils.logger import get_logger
from typing import Dict, Any, Callable, Optional
from src.services.detection.link_detector import LinkHandlerInterface, DetectionResult, auto_register_handler

logger = get_logger(__name__)


@auto_register_handler
class YouTubeHandler(LinkHandlerInterface):
    """Handler for YouTube URLs."""

    # YouTube URL patterns
    YOUTUBE_PATTERNS = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'^https?://(?:www\.)?youtu\.be/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/v/[\w-]+',
        r'^https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
    ]

    @classmethod
    def get_patterns(cls):
        """Get URL patterns for this handler."""
        return cls.YOUTUBE_PATTERNS

    def can_handle(self, url: str) -> DetectionResult:
        """Check if this is a YouTube URL."""
        logger.debug(f"[YOUTUBE_HANDLER] Testing if can handle URL: {url}")

        for pattern in self.YOUTUBE_PATTERNS:
            if re.match(pattern, url):
                logger.info(f"[YOUTUBE_HANDLER] URL matches pattern: {pattern}")
                result = DetectionResult(
                    service_type="youtube",
                    confidence=1.0,
                    metadata={
                        "type": self._detect_youtube_type(url),
                        "video_id": self._extract_video_id(url),
                        "playlist_id": self._extract_playlist_id(url)
                    }
                )
                logger.info(f"[YOUTUBE_HANDLER] Can handle URL with confidence: {result.confidence}")
                logger.debug(f"[YOUTUBE_HANDLER] Detection metadata: {result.metadata}")
                return result

        logger.debug("[YOUTUBE_HANDLER] URL does not match any pattern")
        return DetectionResult(service_type="unknown", confidence=0.0)

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get YouTube metadata for the URL."""
        # This would integrate with your existing YouTube metadata service
        from src.services.youtube.metadata_service import YouTubeMetadataService

        try:
            metadata_service = YouTubeMetadataService()
            video_info = metadata_service.fetch_metadata(url)

            return {
                "title": getattr(video_info, 'title', 'Unknown'),
                "duration": getattr(video_info, 'duration', 0),
                "view_count": getattr(video_info, 'view_count', 0),
                "thumbnail": getattr(video_info, 'thumbnail_url', ''),
                "available_qualities": getattr(video_info, 'available_qualities', []),
                "available_formats": getattr(video_info, 'available_formats', []),
                "available_subtitles": getattr(video_info, 'available_subtitles', [])
            }
        except Exception as e:
            print(f"Error getting YouTube metadata: {e}")
            return {}

    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process YouTube download."""
        # This would integrate with your download system
        print(f"Processing YouTube download: {url}")
        print(f"Options: {options}")
        # Actual download logic would go here
        return True

    def get_ui_callback(self) -> Callable:
        """Get the UI callback for YouTube URLs."""
        logger.info("[YOUTUBE_HANDLER] Getting UI callback")

        from src.ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog
        from src.ui.dialogs.browser_cookie_dialog import BrowserCookieDialog

        def youtube_callback(url: str, ui_context: Any):
            """Callback for handling YouTube URLs."""
            logger.info(f"[YOUTUBE_HANDLER] YouTube callback called with URL: {url}")
            logger.info(f"[YOUTUBE_HANDLER] UI context: {ui_context}")
            logger.info(f"[YOUTUBE_HANDLER] UI context type: {type(ui_context)}")

            # ui_context should be the event coordinator or application orchestrator

            # Get services from ui_context (could be orchestrator or event coordinator)
            container = ui_context.container if hasattr(ui_context, 'container') else ui_context.event_coordinator.container if hasattr(ui_context, 'event_coordinator') else None
            root = ui_context.root if hasattr(ui_context, 'root') else ui_context.event_coordinator.root if hasattr(ui_context, 'event_coordinator') else ui_context

            logger.info(f"[YOUTUBE_HANDLER] Container: {container}")
            logger.info(f"[YOUTUBE_HANDLER] Root: {root}")

            cookie_handler = container.get('cookie_handler') if container else None
            metadata_service = container.get('youtube_metadata') if container else None

            logger.info(f"[YOUTUBE_HANDLER] Cookie handler: {cookie_handler}")
            logger.info(f"[YOUTUBE_HANDLER] Metadata service: {metadata_service}")

            # Use event coordinator for download callback if available
            download_callback = None
            if hasattr(ui_context, 'handle_youtube_download'):
                download_callback = ui_context.handle_youtube_download
                logger.info("[YOUTUBE_HANDLER] Using ui_context handle_youtube_download callback")
            elif hasattr(ui_context, 'event_coordinator'):
                download_callback = ui_context.event_coordinator.handle_youtube_download
                logger.info("[YOUTUBE_HANDLER] Using event_coordinator handle_youtube_download callback")
            else:
                logger.warning("[YOUTUBE_HANDLER] No download callback found in ui_context")

            # Show cookie selection dialog first
            def on_cookie_selected(cookie_path: Optional[str], browser: Optional[str]):
                logger.info(f"[YOUTUBE_HANDLER] Cookie selected: {cookie_path}, browser: {browser}")
                try:
                    # Validate cookie path before proceeding
                    if cookie_path and cookie_handler:
                        success = cookie_handler.set_cookie_file(cookie_path)
                        if not success:
                            logger.error(f"[YOUTUBE_HANDLER] Failed to set cookie file: {cookie_path}")
                            # Continue anyway, the dialog will handle the error
                    
                    YouTubeDownloaderDialog(
                        root,
                        url=url,
                        cookie_handler=cookie_handler,
                        metadata_service=metadata_service,
                        on_download=download_callback,
                        pre_fetched_metadata=None,
                        initial_cookie_path=cookie_path,
                        initial_browser=browser
                    )
                    logger.info("[YOUTUBE_HANDLER] YouTubeDownloaderDialog created successfully")
                except Exception as e:
                    logger.error(f"[YOUTUBE_HANDLER] Failed to create YouTubeDownloaderDialog: {e}", exc_info=True)

            try:
                logger.info("[YOUTUBE_HANDLER] Creating BrowserCookieDialog")
                # Check if root is valid before creating dialog
                if root is None:
                    logger.error("[YOUTUBE_HANDLER] Root is None, cannot create BrowserCookieDialog")
                    return
                    
                BrowserCookieDialog(
                    root,
                    on_cookie_selected
                )
                logger.info("[YOUTUBE_HANDLER] BrowserCookieDialog created successfully")
            except Exception as e:
                logger.error(f"[YOUTUBE_HANDLER] Failed to create BrowserCookieDialog: {e}", exc_info=True)
                # Fallback to direct YouTube downloader dialog without cookies
                try:
                    YouTubeDownloaderDialog(
                        root,
                        url=url,
                        cookie_handler=cookie_handler,
                        metadata_service=metadata_service,
                        on_download=download_callback
                    )
                    logger.info("[YOUTUBE_HANDLER] Created YouTubeDownloaderDialog directly as fallback")
                except Exception as fallback_error:
                    logger.error(f"[YOUTUBE_HANDLER] Fallback also failed: {fallback_error}", exc_info=True)

        logger.info("[YOUTUBE_HANDLER] Returning YouTube callback")
        return youtube_callback

    def _detect_youtube_type(self, url: str) -> str:
        """Detect if URL is video, playlist, etc."""
        if 'playlist?list=' in url:
            return 'playlist'
        elif 'shorts/' in url:
            return 'shorts'
        elif 'watch?v=' in url or 'youtu.be/' in url:
            return 'video'
        elif 'embed/' in url or 'v/' in url:
            return 'embed'
        return 'unknown'

    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _extract_playlist_id(self, url: str) -> Optional[str]:
        """Extract playlist ID from YouTube URL."""
        match = re.search(r'list=([0-9A-Za-z_-]+)', url)
        return match.group(1) if match else None
