"""Service access helper for clean dependency management."""

from typing import Any, Optional
from ..application.container import ServiceContainer


class ServiceAccessor:
    """Provides clean access to services and UI components."""

    def __init__(self, container: ServiceContainer):
        self.container = container

    def get_service(self, service_name: str) -> Optional[Any]:
        """Get a service from the container."""
        return self.container.get(service_name)

    def get_ui_component(self, component_name: str, ui_components: dict) -> Optional[Any]:
        """Get a UI component from the components dictionary."""
        return ui_components.get(component_name)

    # Common service accessors
    @property
    def service_controller(self):
        """Get the service controller."""
        return self.container.get('service_controller')

    @property
    def cookie_handler(self):
        """Get the cookie handler."""
        return self.container.get('cookie_handler')

    @property
    def auth_handler(self):
        """Get the auth handler."""
        return self.container.get('auth_handler')

    @property
    def network_checker(self):
        """Get the network checker."""
        return self.container.get('network_checker')

    @property
    def service_detector(self):
        """Get the service detector."""
        return self.container.get('service_detector')

    @property
    def youtube_metadata(self):
        """Get the YouTube metadata service."""
        return self.container.get('youtube_metadata')

    @property
    def event_coordinator(self):
        """Get the event coordinator."""
        return self.container.get('event_coordinator')