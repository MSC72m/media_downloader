from typing import Any, Callable, Dict, Tuple

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ServiceContainer:
    """Simple service container for dependency management."""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Tuple[Callable[[], Any], bool]] = {}
        self._singletons: Dict[str, Any] = {}

    def register(self, key: str, service: Any, singleton: bool = False) -> None:
        """Register a service instance."""
        if singleton:
            self._singletons[key] = service
            logger.info(
                f"[CONTAINER] Registered singleton: {key} = {type(service).__name__}"
            )
            return None
        self._services[key] = service
        logger.info(f"[CONTAINER] Registered service: {key} = {type(service).__name__}")
        return None

    def register_factory(
        self, key: str, factory: Callable, singleton: bool = False
    ) -> None:
        """Register a service factory."""
        self._factories[key] = (factory, singleton)
        logger.debug(f"Registered factory: {key}")
        return None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a service by key."""
        # Check singletons first
        if key in self._singletons:
            service = self._singletons[key]
            logger.debug(
                f"[CONTAINER] Retrieved singleton: {key} = {type(service).__name__}"
            )
            return service

        # Check regular services
        if key in self._services:
            service = self._services[key]
            logger.debug(
                f"[CONTAINER] Retrieved service: {key} = {type(service).__name__}"
            )
            return service

        # Check factories
        if key in self._factories:
            factory_tuple = self._factories[key]
            factory, is_singleton = factory_tuple
            service = factory()

            if is_singleton:
                self._singletons[key] = service
            else:
                self._services[key] = service

            logger.info(
                f"[CONTAINER] Created service from factory: {key} = {type(service).__name__}"
            )
            return service

        logger.warning(
            f"[CONTAINER] Service not found: {key}, returning default. Available services: {list(self._services.keys())}, singletons: {list(self._singletons.keys())}"
        )
        return default

    def has(self, key: str) -> bool:
        """Check if a service is registered."""
        return any(
            key in d for d in (self._services, self._factories, self._singletons)
        )

    def remove(self, key: str) -> None:
        """Remove a service."""
        self._services.pop(key, None)
        self._factories.pop(key, None)
        self._singletons.pop(key, None)
        logger.debug(f"Removed service: {key}")
        return None

    def clear(self) -> None:
        """Clear all services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
        logger.debug("Cleared all services")
        return None

    def __getitem__(self, key: str) -> Any:
        """Allow dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Allow dictionary-style assignment."""
        self.register(key, value)
        return None

    def __contains__(self, key: str) -> bool:
        """Allow 'in' operator."""
        return self.has(key)
