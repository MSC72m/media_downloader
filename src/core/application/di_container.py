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

        # Create a global namespace that includes the class being resolved
        # This handles forward references like 'ServiceA' -> ServiceA
        global_ns = {}
        class_name = implementation_type.__name__
        global_ns[class_name] = implementation_type

        # Add any registered services to the global namespace for forward reference resolution
        for service_type in self._services:
            global_ns[service_type.__name__] = service_type

        type_hints = get_type_hints(implementation_type.__init__, globalns=global_ns)

        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Skip if parameter has a default value and is not a custom type
            if param.default != param.empty and not self._is_custom_type(type_hints.get(param_name)):
                continue

            param_type = type_hints.get(param_name)
            if param_type and param_type != Any and self._is_custom_type(param_type):
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

    def _is_custom_type(self, param_type: Optional[Type]) -> bool:
        """Check if a type is a custom class that should be injected."""
        if not param_type:
            return False

        # Skip built-in types
        builtin_types = (str, int, float, bool, list, dict, tuple, set)
        if param_type in builtin_types:
            return False

        # Skip typing module types
        from typing import Union, Optional, Any, List, Dict, Tuple, Set
        if param_type in (Union, Optional, Any, List, Dict, Tuple, Set):
            return False

        # Check if it's a user-defined class
        return hasattr(param_type, '__module__') and not param_type.__module__.startswith('typing')

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

    def register_instance(self, service_type: Type[T], instance: T) -> 'ServiceContainer':
        """Register a service instance as singleton."""
        if not isinstance(instance, service_type):
            raise ValueError(f"Instance must be of type {service_type.__name__}")

        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=LifetimeScope.SINGLETON
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        logger.info(f"[CONTAINER] Registered instance: {service_type.__name__}")
        return self

    def register_factory(self, service_type: Type[T], factory: Callable[[], T]) -> 'ServiceContainer':
        """Register a factory for creating services."""
        if not callable(factory):
            raise ValueError("Factory must be callable")

        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifetime=LifetimeScope.TRANSIENT
        )
        self._services[service_type] = descriptor
        logger.info(f"[CONTAINER] Registered factory: {service_type.__name__}")
        return self

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


# Legacy methods for backward compatibility - deprecated
def register(name: str, service: Any) -> None:
    """Legacy registration method - deprecated."""
    logger.warning(f"[CONTAINER] Legacy register() called for '{name}' - this should be removed")

def register_factory(service_type: Type[T], factory: Callable[[], T]) -> 'ServiceContainer':
    """Legacy factory registration - deprecated."""
    logger.warning(f"[CONTAINER] Legacy register_factory() called for {service_type.__name__} - use register_transient() instead")
    # Return a dummy container-like object
    class DummyContainer:
        def validate_dependencies(self): pass
    return DummyContainer()