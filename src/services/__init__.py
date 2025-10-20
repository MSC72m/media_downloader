"""Service layer for the media downloader application."""

from .downloads.factory import ServiceFactory
from .downloads.service import DownloadService
from .downloads.repository import DownloadRepository, OptionsRepository
from .youtube.cookie_detector import CookieManager, CookieDetector
from .file import FileService, DownloadResult, FilenameSanitizer, FileDownloader
from .youtube import YouTubeDownloader
from .twitter import TwitterDownloader
from .instagram import InstagramDownloader
from .pinterest import PinterestDownloader

__all__ = [
    "ServiceFactory",
    "DownloadService",
    "DownloadRepository",
    "OptionsRepository",
    "CookieManager",
    "CookieDetector",
    "FileService",
    "DownloadResult",
    "FilenameSanitizer",
    "FileDownloader",
    "YouTubeDownloader",
    "TwitterDownloader",
    "InstagramDownloader",
    "PinterestDownloader"
]