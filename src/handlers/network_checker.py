"""Concrete implementation of network checker."""

from src.utils.logger import get_logger
from typing import List, Tuple
from ..interfaces import INetworkChecker
from src.core.models import ServiceType
from src.services.network.checker import check_internet_connection, check_site_connection, get_problem_services

logger = get_logger(__name__)


class NetworkChecker(INetworkChecker):
    """Concrete implementation of network checker."""

    def __init__(self):
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the network checker."""
        self._initialized = True
        logger.info("Network checker initialized successfully")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False

    def check_internet_connection(self) -> Tuple[bool, str]:
        """Check general internet connectivity."""
        return check_internet_connection()

    def check_service_connection(self, service: ServiceType) -> Tuple[bool, str]:
        """Check connection to a specific service."""
        try:
            return check_site_connection(service)
        except Exception as e:
            logger.error(f"Error checking service connection for {service.value}: {e}")
            return False, str(e)

    def get_problem_services(self) -> List[str]:
        """Get list of services with connection issues."""
        return get_problem_services()