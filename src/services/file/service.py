"""High-level file service interface."""

from typing import Optional, Callable
from .models import DownloadResult
from .downloader import FileDownloader
from .sanitizer import FilenameSanitizer


class FileService:
    """High-level file service interface."""

    def __init__(self, downloader: Optional[FileDownloader] = None, sanitizer: Optional[FilenameSanitizer] = None):
        self.downloader = downloader or FileDownloader()
        self.sanitizer = sanitizer or FilenameSanitizer()

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename."""
        return self.sanitizer.sanitize_filename(filename)

    def download_file(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> DownloadResult:
        """Download a file with progress monitoring."""
        return self.downloader.download_file(url, save_path, progress_callback)