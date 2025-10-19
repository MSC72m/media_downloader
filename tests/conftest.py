"""Pytest configuration and fixtures."""

import sys
import os

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Mock tkinter and GUI components to avoid import errors
class MockTk:
    def __init__(self, *args, **kwargs):
        pass

class MockCTk:
    def __init__(self, *args, **kwargs):
        pass

# Mock tkinter imports
sys.modules['tkinter'] = MockTk
sys.modules['tkinter.ttk'] = MockTk
sys.modules['tkinter.messagebox'] = MockTk
sys.modules['tkinter.filedialog'] = MockTk
sys.modules['customtkinter'] = MockCTk

# Mock messagebox functions
class MockMessagebox:
    def showerror(self, title, message):
        pass
    def showwarning(self, title, message):
        pass
    def showinfo(self, title, message):
        pass

sys.modules['tkinter.messagebox'] = MockMessagebox()

# Mock GUI components that depend on tkinter
sys.modules['src.utils.window'] = type('MockModule', (), {
    'WindowCenterMixin': object
})()

# Mock logger
class MockLogger:
    def __init__(self, name):
        self.name = name

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

    def debug(self, msg):
        pass

sys.modules['src.utils.logger'] = type('MockModule', (), {
    'get_logger': MockLogger
})()

# Mock interfaces
class MockYouTubeMetadata:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockSubtitleInfo:
    pass

class MockIYouTubeMetadataService:
    pass

sys.modules['src.interfaces.youtube_metadata'] = type('MockModule', (), {
    'YouTubeMetadata': MockYouTubeMetadata,
    'SubtitleInfo': MockSubtitleInfo,
    'IYouTubeMetadataService': MockIYouTubeMetadataService
})()

# Mock other interfaces
class MockBrowserType:
    CHROME = 'chrome'
    FIREFOX = 'firefox'
    SAFARI = 'safari'

class MockPlatformType:
    pass

class MockICookieDetector:
    pass

class MockICookieManager:
    pass

sys.modules['src.interfaces.cookie_detection'] = type('MockModule', (), {
    'BrowserType': MockBrowserType,
    'PlatformType': MockPlatformType,
    'ICookieDetector': MockICookieDetector,
    'ICookieManager': MockICookieManager
})()

# Mock core modules
class MockServiceType:
    YOUTUBE = 'youtube'
    TWITTER = 'twitter'
    INSTAGRAM = 'instagram'
    PINTEREST = 'pinterest'

class MockBaseDownloader:
    pass

sys.modules['src.core'] = type('MockModule', (), {
    'ServiceType': MockServiceType,
    'BaseDownloader': MockBaseDownloader
})()

# Mock services
sys.modules['src.services.factory'] = type('MockModule', (), {
    'ServiceFactory': object
})()

sys.modules['src.services'] = type('MockModule', (), {})()
sys.modules['services'] = type('MockModule', (), {})()
sys.modules['services.youtube'] = type('MockModule', (), {})()
sys.modules['services.youtube.metadata_service'] = type('MockModule', (), {})()

sys.modules['src.services.youtube'] = type('MockModule', (), {
    'YouTubeDownloader': object
})()

sys.modules['src.services.twitter'] = type('MockModule', (), {
    'TwitterDownloader': object
})()

sys.modules['src.services.instagram'] = type('MockModule', (), {
    'InstagramDownloader': object
})()

sys.modules['src.services.pinterest'] = type('MockModule', (), {
    'PinterestDownloader': object
})()

sys.modules['src.services.file'] = type('MockModule', (), {
    'FileService': object
})()

sys.modules['src.services.youtube.cookie_detector'] = type('MockModule', (), {
    'CookieManager': object
})()

# Mock yt-dlp for testing
class MockYoutubeDL:
    def __init__(self, options):
        self.options = options

    def extract_info(self, url, download=False):
        # Return successful mock data for testing
        return {
            'title': 'Test Video',
            'duration': 180,
            'view_count': 1000000,
            'upload_date': '20230101',
            'channel': 'Test Channel',
            'description': 'Test description',
            'thumbnail': 'http://example.com/thumb.jpg',
            'subtitles': {},
            'automatic_captions': {}
        }

    def download(self, urls):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockDownloadError(Exception):
    pass

# Create a proper mock for yt_dlp with nested utils
mock_yt_dlp = type('MockModule', (), {
    'YoutubeDL': MockYoutubeDL,
    'utils': type('MockModule', (), {
        'DownloadError': MockDownloadError
    })()
})()

sys.modules['yt_dlp'] = mock_yt_dlp
sys.modules['yt_dlp.utils'] = mock_yt_dlp.utils

# Mock enums
class MockDownloadStatus:
    PENDING = "Pending"
    DOWNLOADING = "Downloading"
    COMPLETED = "Completed"
    FAILED = "Failed"
    PAUSED = "Paused"
    CANCELLED = "Cancelled"

class MockServiceType:
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"

class MockMessageLevel:
    def __init__(self, value):
        self.value = value
    
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    def __str__(self):
        return self.value
    
    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return self.value == other.value if hasattr(other, 'value') else False

sys.modules['core.enums.download_status'] = type('MockModule', (), {
    'DownloadStatus': MockDownloadStatus
})()

sys.modules['core.enums.service_type'] = type('MockModule', (), {
    'ServiceType': MockServiceType
})()

# Mock models with proper classes
class MockDownload:
    def __init__(self, **kwargs):
        # Set default values
        self.name = kwargs.get('name', '')
        self.url = kwargs.get('url', '')
        self.status = kwargs.get('status', MockDownloadStatus.PENDING)
        self.progress = kwargs.get('progress', 0.0)
        self.speed = kwargs.get('speed', 0.0)
        self.service_type = kwargs.get('service_type')
        self.quality = kwargs.get('quality', '720p')
        self.format = kwargs.get('format', 'video')
        self.audio_only = kwargs.get('audio_only', False)
        self.video_only = kwargs.get('video_only', False)
        self.download_playlist = kwargs.get('download_playlist', False)
        self.download_subtitles = kwargs.get('download_subtitles', False)
        self.selected_subtitles = kwargs.get('selected_subtitles')
        self.download_thumbnail = kwargs.get('download_thumbnail', True)
        self.embed_metadata = kwargs.get('embed_metadata', True)
        self.cookie_path = kwargs.get('cookie_path')
        self.selected_browser = kwargs.get('selected_browser')
        self.speed_limit = kwargs.get('speed_limit')
        self.retries = kwargs.get('retries', 3)
        self.concurrent_downloads = kwargs.get('concurrent_downloads', 1)
        
        # Set any additional kwargs
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)

class MockDownloadOptions:
    def __init__(self, **kwargs):
        self.save_directory = kwargs.get('save_directory', '~/Downloads')
        for k, v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)

class MockUIState:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockAuthState:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class MockButtonState:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

# Mock ServiceController
class MockServiceController:
    def __init__(self, download_service, cookie_manager):
        self.download_service = download_service
        self.cookie_manager = cookie_manager
        self._active_downloads = 0
        self._lock = None  # Mock threading.Lock
    
    def has_active_downloads(self):
        return False
    
    def start_downloads(self, downloads, download_dir, progress_callback=None, completion_callback=None):
        """Mock start_downloads method."""
        # Get download handler from the service
        download_handler = getattr(self.download_service, 'download_handler', None)
        if not download_handler and getattr(self.download_service, 'container', None):
            download_handler = self.download_service.container.get('download_handler')
        
        if download_handler:
            download_handler.start_downloads(
                downloads, 
                download_dir, 
                progress_callback, 
                completion_callback
            )
            return None
        
        if completion_callback:
            completion_callback(False, "No download handler available")
            return None
    
    def _safe_decode_bytes(self, byte_data):
        """Safely decode bytes with multiple fallback encodings."""
        if not byte_data:
            return ""
        
        # Try UTF-8 first (most common)
        try:
            return byte_data.decode('utf-8')
        except UnicodeDecodeError:
            pass
        
        # Try latin-1 (handles all byte values)
        try:
            return byte_data.decode('latin-1')
        except UnicodeDecodeError:
            pass
        
        # Final fallback: replace problematic characters
        try:
            return byte_data.decode('utf-8', errors='replace')
        except Exception:
            # Last resort: use repr to show raw bytes
            return repr(byte_data)

# Add mock models to sys.modules
sys.modules['core.models'] = type('MockModule', (), {
    'Download': MockDownload,
    'DownloadOptions': MockDownloadOptions,
    'UIState': MockUIState,
    'AuthState': MockAuthState,
    'ButtonState': MockButtonState,
    'DownloadStatus': MockDownloadStatus,
    'ServiceType': MockServiceType
})()

sys.modules['core.service_controller'] = type('MockModule', (), {
    'ServiceController': MockServiceController
})()

# Mock enums module for absolute imports
sys.modules['src.core.enums'] = type('MockModule', (), {
    'MessageLevel': MockMessageLevel
})()

# Mock base module
class MockBaseDownloader:
    def __init__(self):
        pass
    
    def download(self, *args, **kwargs):
        pass
    
    def get_metadata(self, *args, **kwargs):
        pass

class MockNetworkError(Exception):
    pass

class MockAuthenticationError(Exception):
    pass

class MockServiceError(Exception):
    pass

sys.modules['core.base'] = type('MockModule', (), {
    'BaseDownloader': MockBaseDownloader,
    'NetworkError': MockNetworkError,
    'AuthenticationError': MockAuthenticationError,
    'ServiceError': MockServiceError
})()

# Only mock what's absolutely necessary for testing
# Remove heavy mocking to allow actual code execution