"""Concrete implementation of service detector."""

from src.utils.logger import get_logger
from typing import Optional
from urllib.parse import urlparse
from ..interfaces import IServiceDetector
from src.core.downloads.models import ServiceType
from src.core.network.checker import check_site_connection

logger = get_logger(__name__)


class ServiceDetector(IServiceDetector):
    """Concrete implementation of service detector."""

    def __init__(self):
        self._domain_to_service = {
            'youtube.com': ServiceType.YOUTUBE,
            'youtu.be': ServiceType.YOUTUBE,
            'twitter.com': ServiceType.TWITTER,
            'x.com': ServiceType.TWITTER,
            'instagram.com': ServiceType.INSTAGRAM,
            'pinterest.com': ServiceType.PINTEREST,
            'pin.it': ServiceType.PINTEREST
        }
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the service detector."""
        self._initialized = True
        logger.info("Service detector initialized successfully")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False

    def detect_service(self, url: str) -> Optional[ServiceType]:
        """Detect service type from URL."""
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

    def is_service_accessible(self, service: ServiceType) -> bool:
        """Check if a service is accessible."""
        try:
            connected, error_msg = check_site_connection(service)
            if not connected:
                logger.warning(f"Service {service.value} not accessible: {error_msg}")
            return connected
        except Exception as e:
            logger.error(f"Error checking service accessibility for {service.value}: {e}")
            return False