from urllib.parse import urlparse

from src.core.config import AppConfig, get_config
from src.core.enums import ServiceType
from src.services.network.checker import check_site_connection
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceDetector:
    """Service detector for identifying service types from URLs.

    Reads service configuration from config.services for dynamic,
    polymorphic service detection.
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize service detector with injected config."""
        self.config = config or get_config()

    def initialize(self) -> None:
        """Initialize the service detector."""
        logger.info("Service detector initialized successfully")

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Service detector cleaned up")

    def detect_service(self, url: str) -> ServiceType | None:
        """Detect service type from URL using config.services.service_types.

        Args:
            url: URL to detect

        Returns:
            ServiceType enum or None if unknown
        """
        try:
            domain = urlparse(url).netloc.lower()

            service_types = self.config.services.service_types

            for domain_pattern, service_type_name in service_types.items():
                if domain_pattern in domain:
                    return ServiceType(service_type_name)

            logger.debug(f"No service detected for domain: {domain}")
            return None

        except Exception as e:
            logger.error(f"Error detecting service for URL {url}: {e}")
            return None

    def is_service_accessible(self, service: ServiceType) -> bool:
        """Check if a service is accessible.

        Args:
            service: ServiceType enum

        Returns:
            True if service is accessible, False otherwise
        """
        try:
            connected, error_msg = check_site_connection(service)
            if not connected:
                logger.warning(f"Service {service.value} not accessible: {error_msg}")
            return connected
        except Exception as e:
            logger.error(f"Error checking service accessibility for {service.value}: {e}")
            return False
