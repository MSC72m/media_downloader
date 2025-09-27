"""Concrete implementation of service detector."""

import logging
from typing import Optional
from urllib.parse import urlparse
from ..interfaces import IServiceDetector, IHandler
from src.core.models import ServiceType
from src.utils.common import check_site_connection

logger = logging.getLogger(__name__)


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
            # Convert ServiceType to service name for check_site_connection
            service_name_map = {
                ServiceType.YOUTUBE: "YouTube",
                ServiceType.TWITTER: "Twitter",
                ServiceType.INSTAGRAM: "Instagram",
                ServiceType.PINTEREST: "Pinterest"
            }
            service_name = service_name_map.get(service)
            if not service_name:
                logger.warning(f"Unknown service type: {service.value}")
                return False

            connected, error_msg = check_site_connection(service_name)
            if not connected:
                logger.warning(f"Service {service.value} not accessible: {error_msg}")
            return connected
        except Exception as e:
            logger.error(f"Error checking service accessibility for {service.value}: {e}")
            return False