import logging
from typing import Dict, Any, Optional, TypeVar, Generic, Callable

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceContainer:
    """Simple service container for dependency management."""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}

    def register(self, key: str, service: Any, singleton: bool = False) -> None:
        """Register a service instance."""
        if singleton:
            self._singletons[key] = service
        else:
            self._services[key] = service
        logger.debug(f"Registered service: {key}")

    def register_factory(self, key: str, factory: Callable, singleton: bool = False) -> None:
        """Register a service factory."""
        self._factories[key] = (factory, singleton)
        logger.debug(f"Registered factory: {key}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get a service by key."""
        # Check singletons first
        if key in self._singletons:
            return self._singletons[key]

        # Check regular services
        if key in self._services:
            return self._services[key]

        # Check factories
        if key in self._factories:
            factory, is_singleton = self._factories[key]
            service = factory()

            if is_singleton:
                self._singletons[key] = service
            else:
                self._services[key] = service

            logger.debug(f"Created service from factory: {key}")
            return service

        return default

    def has(self, key: str) -> bool:
        """Check if a service is registered."""
        return key in self._services or key in self._factories or key in self._singletons

    def remove(self, key: str) -> None:
        """Remove a service."""
        self._services.pop(key, None)
        self._factories.pop(key, None)
        self._singletons.pop(key, None)
        logger.debug(f"Removed service: {key}")

    def clear(self) -> None:
        """Clear all services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Cleared all services")

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style assignment."""
        self.register(key, value)

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return self.has(key)