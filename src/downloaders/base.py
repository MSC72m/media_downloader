"""Base downloader classes and interfaces."""
from abc import ABC, abstractmethod
from typing import Callable, Optional


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