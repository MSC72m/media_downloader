"""Handler implementations for the media downloader application."""

# Import link handlers to trigger auto-registration
from .youtube_handler import YouTubeHandler
from .instagram_handler import InstagramHandler

# Original application handlers
from .application_controller import ApplicationController
from .download_handler import DownloadHandler
from .auth_handler import AuthenticationHandler
from .service_detector import ServiceDetector
from .network_checker import NetworkChecker
from .cookie_handler import CookieHandler

__all__ = [
    # Link handlers
    "YouTubeHandler", "InstagramHandler",
    # Application handlers
    "ApplicationController", "DownloadHandler", "AuthenticationHandler",
    "ServiceDetector", "NetworkChecker", "CookieHandler"
]