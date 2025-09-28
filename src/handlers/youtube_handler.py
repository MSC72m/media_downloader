"""YouTube link handler implementation."""

import re
from typing import Dict, Any, Callable, Optional
from ..core.link_detection import LinkHandlerInterface, DetectionResult, auto_register_handler


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
        for pattern in self.YOUTUBE_PATTERNS:
            if re.match(pattern, url):
                return DetectionResult(
                    service_type="youtube",
                    confidence=1.0,
                    metadata={
                        "type": self._detect_youtube_type(url),
                        "video_id": self._extract_video_id(url),
                        "playlist_id": self._extract_playlist_id(url)
                    }
                )
        return DetectionResult(service_type="unknown", confidence=0.0)

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get YouTube metadata for the URL."""
        # This would integrate with your existing YouTube metadata service
        from ..services.youtube.metadata_service import YouTubeMetadataService

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
        from ..ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog
        from ..ui.dialogs.browser_cookie_dialog import BrowserCookieDialog

        def youtube_callback(url: str, ui_context: Any):
            """Callback for handling YouTube URLs."""
            # ui_context should be the event coordinator or application orchestrator

            # Get services from ui_context (could be orchestrator or event coordinator)
            container = ui_context.container if hasattr(ui_context, 'container') else ui_context.event_coordinator.container if hasattr(ui_context, 'event_coordinator') else None
            root = ui_context.root if hasattr(ui_context, 'root') else ui_context.event_coordinator.root if hasattr(ui_context, 'event_coordinator') else ui_context

            cookie_handler = container.get('cookie_handler') if container else None
            metadata_service = container.get('youtube_metadata') if container else None

            # Use event coordinator for download callback if available
            download_callback = None
            if hasattr(ui_context, 'handle_youtube_download'):
                download_callback = ui_context.handle_youtube_download
            elif hasattr(ui_context, 'event_coordinator'):
                download_callback = ui_context.event_coordinator.handle_youtube_download

            # Show cookie selection dialog first
            def on_cookie_selected(cookie_path: Optional[str], browser: Optional[str]):
                dialog = YouTubeDownloaderDialog(
                    root,
                    url=url,
                    cookie_handler=cookie_handler,
                    metadata_service=metadata_service,
                    on_download=download_callback,
                    pre_fetched_metadata=None,
                    initial_cookie_path=cookie_path,
                    initial_browser=browser
                )

            cookie_dialog = BrowserCookieDialog(
                root,
                on_cookie_selected
            )

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