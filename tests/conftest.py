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

sys.modules['yt_dlp'] = type('MockModule', (), {
    'YoutubeDL': MockYoutubeDL
})()

sys.modules['yt_dlp.utils'] = type('MockModule', (), {
    'DownloadError': MockDownloadError
})()