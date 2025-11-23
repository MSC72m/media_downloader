"""Type-safe dependency injection container."""

from abc import ABC, abstractmethod
from enum import Enum, auto
from inspect import isclass, signature
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    get_type_hints,
    get_origin,
    get_args,
)

from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class LifetimeScope(Enum):
    """Service lifetime scope."""
    SINGLETON = auto()
    TRANSIENT = auto()


class ServiceDescriptor:
    """Describes a service registration."""

    def __init__(
        self,
        service_type: Type,
        implementation: Optional[Type] = None,
        factory: Optional[Callable] = None,
        instance: Optional[Any] = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime

    def validate(self) -> None:
        """Validate the service descriptor."""
        implementation_count = sum([
            self.implementation is not None,
            self.factory is not None,
            self.instance is not None
        ])

        if implementation_count != 1:
            raise ValueError(
                f"Exactly one of implementation, factory, or instance must be provided "
                f"for service type {self.service_type.__name__}"
            )


class ServiceContainer:
    """Type-safe dependency injection container."""

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._singletons: Dict[Type, Any] = {}
        self._building: set[Type] = set()  # Track circular dependencies

    def register_transient(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None
    ) -> 'ServiceContainer':
        """Register a transient service (new instance each time)."""
        return self._register_service(
            service_type, implementation, factory, LifetimeScope.TRANSIENT
        )

    def register_singleton(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        instance: Optional[T] = None
    ) -> 'ServiceContainer':
        """Register a singleton service (same instance each time)."""
        if instance is not None:
            self._singletons[service_type] = instance
            logger.info(f"[CONTAINER] Registered singleton instance: {service_type.__name__}")
            return self

        return self._register_service(
            service_type, implementation, factory, LifetimeScope.SINGLETON
        )

    def _register_service(
        self,
        service_type: Type[T],
        implementation: Optional[Type[T]] = None,
        factory: Optional[Callable[[], T]] = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT
    ) -> 'ServiceContainer':
        """Internal service registration method."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            factory=factory,
            lifetime=lifetime
        )

        descriptor.validate()
        self._services[service_type] = descriptor

        logger.info(
            f"[CONTAINER] Registered {lifetime.name.lower()}: "
            f"{service_type.__name__} -> {descriptor.implementation.__name__}"
        )

        return self

    def get(self, service_type: Type[T]) -> T:
        """Resolve a service instance."""
        if service_type in self._building:
            raise ValueError(f"Circular dependency detected: {service_type.__name__}")

        # Check for existing singleton
        if service_type in self._singletons:
            instance = self._singletons[service_type]
            logger.debug(f"[CONTAINER] Retrieved singleton: {service_type.__name__}")
            return instance

        # Get service descriptor
        if service_type not in self._services:
            raise ValueError(f"Service not registered: {service_type.__name__}")

        descriptor = self._services[service_type]

        # Create instance based on registration type
        if descriptor.instance is not None:
            return descriptor.instance

        # Mark as building to detect circular dependencies
        self._building.add(service_type)

        try:
            if descriptor.factory:
                instance = descriptor.factory()
            else:
                instance = self._create_instance(descriptor.implementation)

            # Store singleton if needed
            if descriptor.lifetime == LifetimeScope.SINGLETON:
                self._singletons[service_type] = instance

            logger.debug(f"[CONTAINER] Created {descriptor.lifetime.name.lower()}: {service_type.__name__}")
            return instance

        finally:
            self._building.discard(service_type)

    def _create_instance(self, implementation_type: Type[T]) -> T:
        """Create instance with constructor injection."""
        if not hasattr(implementation_type, '__init__'):
            return implementation_type()

        sig = signature(implementation_type.__init__)
        type_hints = get_type_hints(implementation_type.__init__)

        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_type = type_hints.get(param_name)
            if param_type and param_type != Any:
                # Handle Optional[T] types - provide None if not registered
                origin = get_origin(param_type)
                if origin is Union and type(None) in get_args(param_type):
                    # Optional type - try to get dependency, use None if not found
                    non_none_type = next(t for t in get_args(param_type) if t is not type(None))
                    if self.has(non_none_type):
                        kwargs[param_name] = self.get(non_none_type)
                    else:
                        kwargs[param_name] = None
                else:
                    # Required dependency
                    kwargs[param_name] = self.get(param_type)

        return implementation_type(**kwargs)

    def get_optional(self, service_type: Type[T]) -> Optional[T]:
        """Resolve a service instance, returning None if not registered."""
        try:
            return self.get(service_type)
        except ValueError:
            return None

    def has(self, service_type: Type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services or service_type in self._singletons

    def clear(self) -> None:
        """Clear all services and singletons."""
        self._services.clear()
        self._singletons.clear()
        logger.debug("[CONTAINER] Cleared all services")

    def validate_dependencies(self) -> None:
        """Validate that all registered dependencies can be resolved."""
        logger.info("[CONTAINER] Validating dependencies")

        for service_type, descriptor in self._services.items():
            try:
                # Try to resolve the service
                self.get(service_type)
                logger.debug(f"[CONTAINER] ✓ {service_type.__name__}")
            except Exception as e:
                logger.error(f"[CONTAINER] ✗ {service_type.__name__}: {e}")
                raise ValueError(f"Dependency validation failed for {service_type.__name__}: {e}")

        logger.info("[CONTAINER] All dependencies validated successfully")


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = ServiceContainer()
    return _container


def configure_container(configurator: Callable[[ServiceContainer], None]) -> None:
    """Configure the global container."""
    container = get_container()
    configurator(container)
    container.validate_dependencies()


def auto_register_by_convention(container: ServiceContainer, module_path: str) -> None:
    """Auto-register services by convention.

    Services are registered as singletons with interface->implementation mappings.
    Implementation classes should implement interfaces and follow naming convention:
    - Interface: IMyService
    - Implementation: MyService
    """
    import importlib
    import inspect

    try:
        module = importlib.import_module(module_path)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Skip if it's a private class or from another module
            if name.startswith('_') or obj.__module__ != module.__name__:
                continue

            # Find interfaces this class implements
            interfaces = [base for base in obj.__bases__ if hasattr(base, '__abstractmethods__')]

            if interfaces:
                # Register with the first interface found
                interface = interfaces[0]
                container.register_singleton(interface, obj)
                logger.info(f"[AUTO_REGISTER] {name} -> {interface.__name__}")
            else:
                # Register concrete class as itself
                container.register_singleton(obj, obj)
                logger.info(f"[AUTO_REGISTER] {name} -> {name}")

    except ImportError as e:
        logger.warning(f"[AUTO_REGISTER] Failed to import module {module_path}: {e}")


def inject(dependency_type: Type[T]) -> T:
    """Dependency injection decorator for automatic parameter injection."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()
            return func(container.get(dependency_type), *args, **kwargs)
        return wrapper
    return decorator