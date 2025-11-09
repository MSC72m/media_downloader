"""Base classes and interfaces for the media downloader application."""

from abc import ABC, abstractmethod
from typing import Callable, Optional
import os


class BaseDownloader(ABC):
    """Base class for all media downloaders."""

    @abstractmethod
    def download(
        self,
        url: str,
        save_path: str,
        progress_callback: Optional[Callable[[float, float], None]] = None
    ) -> bool:
        """
        Download media from a URL.

        Args:
            url: URL to download from
            save_path: Path to save the downloaded media
            progress_callback: Callback for progress updates (progress percentage, speed)

        Returns:
            True if download was successful, False otherwise
        """
        pass

    def _ensure_directory_exists(self, file_path: str) -> None:
        """
        Ensure the directory for the given file path exists.

        Args:
            file_path: Full path to the file
        """
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _get_save_directory(self, save_path: str) -> str:
        """
        Extract directory path from save path.

        Args:
            save_path: Full path or directory path

        Returns:
            Directory path
        """
        return os.path.dirname(save_path) if os.path.dirname(save_path) else "."


class NetworkError(Exception):
    """Exception raised for network-related errors."""

    def __init__(self, message: str, is_temporary: bool = False):
        """
        Initialize network error.

        Args:
            message: Error message
            is_temporary: Whether the error is likely temporary (e.g., rate limiting)
        """
        self.message = message
        self.is_temporary = is_temporary
        super().__init__(self.message)


class AuthenticationError(Exception):
    """Exception raised for authentication errors."""

    def __init__(self, message: str, service: str = ""):
        """
        Initialize authentication error.

        Args:
            message: Error message
            service: Service name where auth failed
        """
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)


class ServiceError(Exception):
    """Exception raised for service-related errors."""

    def __init__(self, message: str, service: str = ""):
        """
        Initialize service error.

        Args:
            message: Error message
            service: Service name where error occurred
        """
        self.message = message
        self.service = service
        super().__init__(f"{service}: {message}" if service else message)
