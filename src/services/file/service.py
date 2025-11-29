import os
from collections.abc import Callable

from .downloader import FileDownloader
from .models import DownloadResult
from .sanitizer import FilenameSanitizer


class FileService:
    def __init__(
        self,
        downloader: FileDownloader | None = None,
        sanitizer: FilenameSanitizer | None = None,
    ):
        self.downloader = downloader or FileDownloader()
        self.sanitizer = sanitizer or FilenameSanitizer()

    def sanitize_filename(self, filename: str) -> str:
        return self.sanitizer.sanitize_filename(filename)

    def clean_filename(self, filename: str) -> str:
        return self.sanitize_filename(filename)

    def ensure_directory(self, path: str) -> bool:
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False

    def get_unique_filename(self, directory: str, base_name: str, extension: str) -> str:
        base_name = self.sanitize_filename(base_name)
        filename = f"{base_name}{extension}"
        full_path = os.path.join(directory, filename)

        if not os.path.exists(full_path):
            return filename

        counter = 1
        while True:
            new_filename = f"{base_name}_{counter}{extension}"
            new_full_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_full_path):
                return new_filename
            counter += 1

    def download_file(
        self,
        url: str,
        save_path: str,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> DownloadResult:
        return self.downloader.download_file(url, save_path, progress_callback)

    def save_text_file(self, content: str, file_path: str) -> bool:
        try:
            directory = os.path.dirname(file_path)
            self.ensure_directory(directory)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception:
            return False
