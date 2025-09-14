"""Network connectivity services following SOLID principles."""
import socket
import http.client
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Tuple, List, Optional, Protocol
from dataclasses import dataclass
from src.models.enums.core import ServiceType

logger = logging.getLogger(__name__)

@dataclass
class ConnectionResult:
    """Result of a connection check."""
    is_connected: bool
    error_message: str = ""
    response_time: float = 0.0
    service_type: Optional[ServiceType] = None

class NetworkChecker(Protocol):
    """Protocol for network checking services."""
    def check_connectivity(self) -> ConnectionResult: ...
    def check_service(self, service: ServiceType) -> ConnectionResult: ...
    def check_all_services(self) -> Dict[ServiceType, ConnectionResult]: ...

class BaseNetworkChecker(ABC):
    """Abstract base class for network checkers."""

    @abstractmethod
    def check_connectivity(self) -> ConnectionResult:
        """Check basic internet connectivity."""
        pass

    @abstractmethod
    def check_service(self, service: ServiceType) -> ConnectionResult:
        """Check connectivity to a specific service."""
        pass

class HTTPNetworkChecker(BaseNetworkChecker):
    """HTTP-based network checker."""

    DEFAULT_TIMEOUT = 10  # seconds
    SERVICE_URLS = {
        ServiceType.GOOGLE: "www.google.com",
        ServiceType.YOUTUBE: "www.youtube.com",
        ServiceType.INSTAGRAM: "www.instagram.com",
        ServiceType.TWITTER: "x.com",  # Updated to current Twitter domain
        ServiceType.PINTEREST: "www.pinterest.com"
    }

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

    def check_connectivity(self) -> ConnectionResult:
        """Check basic internet connectivity using Google DNS."""
        start_time = time.time()

        try:
            # Check basic DNS connectivity
            socket.create_connection(("8.8.8.8", 53), timeout=self.timeout)

            # Check HTTP connectivity to Google
            return self.check_service(ServiceType.GOOGLE)

        except OSError as e:
            response_time = time.time() - start_time
            return ConnectionResult(
                is_connected=False,
                error_message=f"Cannot connect to network: {str(e)}",
                response_time=response_time
            )

    def check_service(self, service: ServiceType) -> ConnectionResult:
        """Check connectivity to a specific service using progressive reliability checks."""
        start_time = time.time()

        if service not in self.SERVICE_URLS:
            return ConnectionResult(
                is_connected=False,
                error_message=f"Unknown service: {service}",
                response_time=time.time() - start_time,
                service_type=service
            )

        url = self.SERVICE_URLS[service]

        # Step 1: Check DNS resolution (most basic connectivity)
        try:
            socket.gethostbyname(url)
            dns_time = time.time() - start_time
        except socket.gaierror:
            response_time = time.time() - start_time
            return ConnectionResult(
                is_connected=False,
                error_message=f"Cannot resolve {service} - check internet connection",
                response_time=response_time,
                service_type=service
            )
        except Exception:
            response_time = time.time() - start_time
            return ConnectionResult(
                is_connected=False,
                error_message=f"DNS error for {service}",
                response_time=response_time,
                service_type=service
            )

        # Step 2: Try basic socket connection (port 443 for HTTPS)
        try:
            sock = socket.create_connection((url, 443), timeout=self.timeout)
            sock.close()
            socket_time = time.time() - start_time
            return ConnectionResult(
                is_connected=True,
                response_time=socket_time,
                service_type=service
            )
        except Exception:
            socket_time = time.time() - start_time

            # Step 3: If socket fails, try HTTP as fallback (some services block direct socket)
            try:
                conn = http.client.HTTPSConnection(url, timeout=self.timeout)
                conn.request("HEAD", "/", headers={"User-Agent": "Mozilla/5.0"})
                response = conn.getresponse()
                conn.close()

                http_time = time.time() - start_time

                if 200 <= response.status < 400:
                    return ConnectionResult(
                        is_connected=True,
                        response_time=http_time,
                        service_type=service
                    )
                elif response.status in [401, 403]:
                    # Authentication required, but service is reachable
                    return ConnectionResult(
                        is_connected=True,
                        response_time=http_time,
                        service_type=service
                    )
                elif response.status == 429:
                    return ConnectionResult(
                        is_connected=False,
                        error_message=f"{service} is rate limiting requests",
                        response_time=http_time,
                        service_type=service
                    )
                else:
                    return ConnectionResult(
                        is_connected=False,
                        error_message=f"{service} returned HTTP {response.status}",
                        response_time=http_time,
                        service_type=service
                    )

            except Exception:
                response_time = time.time() - start_time
                return ConnectionResult(
                    is_connected=False,
                    error_message=f"{service} is reachable but service unavailable",
                    response_time=response_time,
                    service_type=service
                )

    def check_all_services(self) -> Dict[ServiceType, ConnectionResult]:
        """Check connectivity to all supported services."""
        results = {}

        for service in self.SERVICE_URLS:
            try:
                result = self.check_service(service)
                results[service] = result
            except Exception as e:
                logger.error(f"Error checking service {service}: {str(e)}")
                results[service] = ConnectionResult(
                    is_connected=False,
                    error_message=str(e),
                    service_type=service
                )

        return results

class NetworkService:
    """High-level network service interface."""

    def __init__(self, checker: NetworkChecker = None):
        self.checker = checker or HTTPNetworkChecker()

    def check_internet_connection(self) -> Tuple[bool, str]:
        """Check if the device has working internet connection."""
        result = self.checker.check_connectivity()
        return result.is_connected, result.error_message

    def check_site_connection(self, service: ServiceType) -> Tuple[bool, str]:
        """Check connectivity to a specific service."""
        result = self.checker.check_service(service)
        return result.is_connected, result.error_message

    def check_all_services(self) -> Dict[ServiceType, Tuple[bool, str]]:
        """Check connectivity to all services."""
        results = self.checker.check_all_services()
        return {
            service: (result.is_connected, result.error_message)
            for service, result in results.items()
        }

    def get_problem_services(self) -> List[ServiceType]:
        """Get a list of services with connectivity issues."""
        results = self.checker.check_all_services()
        return [
            service for service, result in results.items()
            if not result.is_connected
        ]

    def is_service_connected(self, service: ServiceType) -> bool:
        """Check if a specific service is connected."""
        result = self.checker.check_service(service)
        return result.is_connected

# For backward compatibility
def check_internet_connection() -> Tuple[bool, str]:
    """Legacy function for backward compatibility."""
    service = NetworkService()
    return service.check_internet_connection()

def check_site_connection(service: ServiceType) -> Tuple[bool, str]:
    """Legacy function for backward compatibility."""
    network_service = NetworkService()
    return network_service.check_site_connection(service)

def check_all_services() -> Dict[ServiceType, Tuple[bool, str]]:
    """Legacy function for backward compatibility."""
    service = NetworkService()
    return service.check_all_services()

def get_problem_services() -> List[ServiceType]:
    """Legacy function for backward compatibility."""
    service = NetworkService()
    return service.get_problem_services()

def is_service_connected(service: ServiceType) -> bool:
    """Legacy function for backward compatibility."""
    service_obj = NetworkService()
    return service_obj.is_service_connected(service)