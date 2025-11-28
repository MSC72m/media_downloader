"""Concrete implementation of network checker."""

from typing import List, Optional, Tuple

from src.core.enums import ServiceType
from src.core.interfaces import IErrorNotifier
from src.services.network.checker import (
    check_internet_connection,
    check_site_connection,
    get_problem_services,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NetworkChecker:
    """Network checker for verifying connectivity to services."""

    def __init__(self, error_handler: Optional[IErrorNotifier] = None):
        """Initialize network checker.

        Args:
            error_handler: Optional error handler for user notifications
        """
        self._initialized = False
        self.error_handler = error_handler

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

    def check_connectivity(self) -> Tuple[bool, str]:
        """Check network connectivity - alias for check_internet_connection."""
        return self.check_internet_connection()

    def check_service_connection(self, service: ServiceType) -> Tuple[bool, str]:
        """Check connection to a specific service."""
        try:
            return check_site_connection(service)
        except Exception as e:
            error_msg = f"Error checking service connection for {service.value}: {e}"
            logger.error(error_msg, exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, f"Checking {service.value} connection", "Network Checker"
                )
            return False, str(e)

    def get_problem_services(self) -> List[str]:
        """Get list of services with connection issues."""
        return get_problem_services()
