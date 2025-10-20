"""Service factory for creating appropriate services based on URL."""

from src.utils.logger import get_logger
from typing import Optional, Dict
from urllib.parse import urlparse
from ..core.models import ServiceType
from ..core.base import BaseDownloader
from .youtube import YouTubeDownloader
from .twitter import TwitterDownloader
from .instagram import InstagramDownloader
from .pinterest import PinterestDownloader
from .youtube.cookie_detector import CookieManager
from .file import FileService

logger = get_logger(__name__)


class ServiceFactory:
    """Factory for creating appropriate services based on URL and service type."""

    def __init__(self, cookie_manager: Optional[CookieManager] = None):
        self._cookie_manager = cookie_manager
        self._file_service = FileService()
        self._initialize_services()

    def _initialize_services(self):
        """Initialize all available services."""
        self._downloaders: Dict[ServiceType, BaseDownloader] = {
            ServiceType.YOUTUBE: YouTubeDownloader(
                cookie_manager=self._cookie_manager
            ),
            ServiceType.TWITTER: TwitterDownloader(),
            ServiceType.INSTAGRAM: InstagramDownloader(),
            ServiceType.PINTEREST: PinterestDownloader(),
        }

        self._domain_to_service = {
            'youtube.com': ServiceType.YOUTUBE,
            'youtu.be': ServiceType.YOUTUBE,
            'twitter.com': ServiceType.TWITTER,
            'x.com': ServiceType.TWITTER,
            'instagram.com': ServiceType.INSTAGRAM,
            'pinterest.com': ServiceType.PINTEREST,
            'pin.it': ServiceType.PINTEREST
        }

    def get_downloader(self, url: str) -> Optional[BaseDownloader]:
        """
        Get the appropriate downloader for a URL.

        Args:
            url: URL to get downloader for

        Returns:
            Appropriate downloader or None if not supported
        """
        service_type = self.detect_service_type(url)
        if service_type and service_type in self._downloaders:
            return self._downloaders[service_type]
        return None

    def detect_service_type(self, url: str) -> Optional[ServiceType]:
        """
        Detect service type from URL.

        Args:
            url: URL to analyze

        Returns:
            Service type or None if not supported
        """
        try:
            domain = urlparse(url).netloc.lower()

            # Check for exact matches first
            if domain in self._domain_to_service:
                return self._domain_to_service[domain]

            # Check for partial matches
            for domain_pattern, service_type in self._domain_to_service.items():
                if domain_pattern in domain:
                    return service_type

            logger.debug(f"No service detected for domain: {domain}")
            return None

        except Exception as e:
            logger.error(f"Error detecting service for URL {url}: {e}")
            return None

    def get_supported_services(self) -> list[ServiceType]:
        """Get list of supported services."""
        return list(self._downloaders.keys())

    def is_service_supported(self, service_type: ServiceType) -> bool:
        """Check if a service is supported."""
        return service_type in self._downloaders

    def get_file_service(self) -> FileService:
        """Get the file service."""
        return self._file_service

    def get_cookie_manager(self) -> Optional[CookieManager]:
        """Get the cookie manager."""
        return self._cookie_manager

    def update_downloader_options(self, service_type: ServiceType, **kwargs) -> bool:
        """
        Update downloader options for a specific service.

        Args:
            service_type: Service type to update
            **kwargs: Options to update

        Returns:
            True if successful, False otherwise
        """
        if service_type not in self._downloaders:
            return False

        try:
            downloader = self._downloaders[service_type]
            if hasattr(downloader, 'update_options'):
                downloader.update_options(**kwargs)
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating {service_type} downloader options: {e}")
            return False