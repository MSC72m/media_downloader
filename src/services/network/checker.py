"""Network connectivity services following SOLID principles."""

import http.client
import socket
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Protocol, Tuple

from pydantic import BaseModel, Field

from src.core.enums import ServiceType
from src.interfaces.service_interfaces import IErrorHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionResult(BaseModel):
    """Result of a connection check."""
    is_connected: bool = Field(description="Whether the connection was successful")
    error_message: str = Field(default="", description="Error message if connection failed")
    response_time: float = Field(default=0.0, description="Response time in seconds")
    service_type: Optional[ServiceType] = Field(default=None, description="Type of service checked")

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

    def __init__(self, timeout: Optional[int] = None, error_handler: Optional[IErrorHandler] = None):
        """Initialize network checker.
        
        Args:
            timeout: Network timeout in seconds (uses config if not provided)
            error_handler: Error handler instance
        """
        from src.core.config import get_config
        
        config = get_config()
        self.timeout = timeout or config.network.default_timeout
        self.error_handler = error_handler
        self.user_agent = config.network.user_agent
        self._service_configs = self._get_service_configs()
    
    def _get_service_configs(self):
        """Get service-specific configurations using config."""
        return {
            ServiceType.TWITTER: {
                'requires_js': True,
                'fallback_urls': ['api.x.com', 'mobile.x.com'],
                'user_agent': self.user_agent,
                'check_endpoints': ['/', '/i/flow/login']
            },
            ServiceType.YOUTUBE: {
                'requires_js': True,
                'fallback_urls': ['www.youtube.com', 'm.youtube.com', 'music.youtube.com'],
                'user_agent': self.user_agent,
                'check_endpoints': ['/', '/watch', '/feed/trending']
            },
            ServiceType.INSTAGRAM: {
                'requires_js': True,
                'fallback_urls': ['www.instagram.com', 'm.instagram.com', 'graph.instagram.com'],
                'user_agent': self.user_agent,
                'check_endpoints': ['/', '/explore/', '/accounts/login/']
            }
        }
    
    SERVICE_URLS = {
        ServiceType.GOOGLE: "www.google.com",
        ServiceType.YOUTUBE: "www.youtube.com",
        ServiceType.INSTAGRAM: "www.instagram.com",
        ServiceType.TWITTER: "x.com",  # Updated to current Twitter domain
        ServiceType.PINTEREST: "www.pinterest.com"
    }


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

        # Use service-specific checking for Twitter/X, YouTube, and Instagram
        if service == ServiceType.TWITTER:
            return self._check_twitter_connectivity(start_time)
        elif service == ServiceType.YOUTUBE:
            return self._check_youtube_connectivity(start_time)
        elif service == ServiceType.INSTAGRAM:
            return self._check_instagram_connectivity(start_time)

        url = self.SERVICE_URLS[service]

        # Step 1: Check DNS resolution (most basic connectivity)
        try:
            socket.gethostbyname(url)
            # dns_time = time.time() - start_time
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

    def _check_twitter_connectivity(self, start_time: float) -> ConnectionResult:
        """Specialized connectivity checking for Twitter/X."""
        config = self._service_configs.get(ServiceType.TWITTER, {})
        primary_url = self.SERVICE_URLS[ServiceType.TWITTER]

        # Try primary domain first
        result = self._try_twitter_urls([primary_url], start_time, config)
        if result.is_connected:
            return result

        # Try fallback URLs if primary fails
        fallback_urls = config.get('fallback_urls', [])
        if fallback_urls:
            result = self._try_twitter_urls(fallback_urls, start_time, config)
            if result.is_connected:
                return result

        # If all else fails, try a more lenient check
        return self._lenient_twitter_check(start_time)

    def _try_service_urls(self, urls: List[str], start_time: float, config: dict, service_type: ServiceType) -> ConnectionResult:
        """Generic method to try multiple URLs for any service connectivity."""
        user_agent = config.get('user_agent', 'Mozilla/5.0')
        service_name = service_type.value if hasattr(service_type, 'value') else str(service_type)

        for url in urls:
            try:
                # Step 1: DNS resolution
                socket.gethostbyname(url)

                # Step 2: Try socket connection
                try:
                    sock = socket.create_connection((url, 443), timeout=self.timeout)
                    sock.close()
                    socket_time = time.time() - start_time
                    return ConnectionResult(
                        is_connected=True,
                        response_time=socket_time,
                        service_type=service_type
                    )
                except Exception:
                    pass

                # Step 3: Try HTTP with specific endpoints
                endpoints = config.get('check_endpoints', ['/'])
                for endpoint in endpoints:
                    try:
                        conn = http.client.HTTPSConnection(url, timeout=self.timeout)
                        conn.request("HEAD", endpoint, headers={
                            "User-Agent": user_agent,
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                            "Accept-Language": "en-US,en;q=0.5",
                            "Accept-Encoding": "gzip, deflate",
                            "DNT": "1",
                            "Connection": "keep-alive",
                            "Upgrade-Insecure-Requests": "1"
                        })
                        response = conn.getresponse()
                        conn.close()

                        http_time = time.time() - start_time

                        # Check for successful response codes
                        if response.status in [200, 301, 302, 307, 308]:
                            return ConnectionResult(
                                is_connected=True,
                                response_time=http_time,
                                service_type=service_type
                            )
                        elif response.status in [401, 403]:
                            # Auth required but service is reachable
                            return ConnectionResult(
                                is_connected=True,
                                response_time=http_time,
                                service_type=service_type
                            )
                        elif response.status == 429:
                            return ConnectionResult(
                                is_connected=False,
                                error_message=f"{service_name} is rate limiting requests",
                                response_time=http_time,
                                service_type=service_type
                            )

                    except Exception:
                        continue

            except socket.gaierror:
                # DNS failed for this URL, try next one
                continue
            except Exception:
                # Other error, try next URL
                continue

        # All URLs failed
        response_time = time.time() - start_time
        return ConnectionResult(
            is_connected=False,
            error_message=f"Cannot connect to {service_name} - service may be down or restricted in your region",
            response_time=response_time,
            service_type=service_type
        )

    def _try_twitter_urls(self, urls: List[str], start_time: float, config: dict) -> ConnectionResult:
        """Try multiple URLs for Twitter connectivity."""
        return self._try_service_urls(urls, start_time, config, ServiceType.TWITTER)

    def _lenient_service_check(self, start_time: float, service_type: ServiceType, primary_domain: str) -> ConnectionResult:
        """Generic lenient check for service connectivity using DNS resolution."""
        service_name = service_type.value if hasattr(service_type, 'value') else str(service_type)
        try:
            # Try to resolve DNS for the primary domain as a basic check
            socket.gethostbyname(primary_domain)
            response_time = time.time() - start_time

            # If DNS resolves, assume service is accessible even if HTTP fails
            # This is more lenient but works better for services with complex routing
            return ConnectionResult(
                is_connected=True,
                response_time=response_time,
                service_type=service_type
            )
        except Exception as e:
            response_time = time.time() - start_time
            return ConnectionResult(
                is_connected=False,
                error_message=f"{service_name} DNS resolution failed: {str(e)}",
                response_time=response_time,
                service_type=service_type
            )

    def _lenient_twitter_check(self, start_time: float) -> ConnectionResult:
        """More lenient check for Twitter/X connectivity."""
        return self._lenient_service_check(start_time, ServiceType.TWITTER, "x.com")

    def _check_youtube_connectivity(self, start_time: float) -> ConnectionResult:
        """Specialized connectivity checking for YouTube."""
        config = self._service_configs.get(ServiceType.YOUTUBE, {})
        primary_url = self.SERVICE_URLS[ServiceType.YOUTUBE]

        # Try primary domain first
        result = self._try_youtube_urls([primary_url], start_time, config)
        if result.is_connected:
            return result

        # Try fallback URLs if primary fails
        fallback_urls = config.get('fallback_urls', [])
        if fallback_urls:
            result = self._try_youtube_urls(fallback_urls, start_time, config)
            if result.is_connected:
                return result

        # If all else fails, try a more lenient check
        return self._lenient_youtube_check(start_time)

    def _check_instagram_connectivity(self, start_time: float) -> ConnectionResult:
        """Specialized connectivity checking for Instagram."""
        config = self._service_configs.get(ServiceType.INSTAGRAM, {})
        primary_url = self.SERVICE_URLS[ServiceType.INSTAGRAM]

        # Try primary domain first
        result = self._try_instagram_urls([primary_url], start_time, config)
        if result.is_connected:
            return result

        # Try fallback URLs if primary fails
        fallback_urls = config.get('fallback_urls', [])
        if fallback_urls:
            result = self._try_instagram_urls(fallback_urls, start_time, config)
            if result.is_connected:
                return result

        # If all else fails, try a more lenient check
        return self._lenient_instagram_check(start_time)

    def _try_youtube_urls(self, urls: List[str], start_time: float, config: dict) -> ConnectionResult:
        """Try multiple URLs for YouTube connectivity."""
        return self._try_service_urls(urls, start_time, config, ServiceType.YOUTUBE)

    def _try_instagram_urls(self, urls: List[str], start_time: float, config: dict) -> ConnectionResult:
        """Try multiple URLs for Instagram connectivity."""
        return self._try_service_urls(urls, start_time, config, ServiceType.INSTAGRAM)

    def _lenient_youtube_check(self, start_time: float) -> ConnectionResult:
        """More lenient check for YouTube connectivity."""
        return self._lenient_service_check(start_time, ServiceType.YOUTUBE, "youtube.com")

    def _lenient_instagram_check(self, start_time: float) -> ConnectionResult:
        """More lenient check for Instagram connectivity."""
        return self._lenient_service_check(start_time, ServiceType.INSTAGRAM, "instagram.com")

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

    def __init__(self, checker: Optional[NetworkChecker] = None, error_handler: Optional[IErrorHandler] = None):
        self.checker = checker or HTTPNetworkChecker(error_handler=error_handler)

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
