"""Type-safe dependency injection container."""

import types
from collections.abc import Callable
from enum import Enum, auto
from inspect import signature
from typing import (
    Any,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

T = TypeVar("T")


class LifetimeScope(Enum):
    """Service lifetime scope."""

    SINGLETON = auto()
    TRANSIENT = auto()


class ServiceDescriptor:
    """Describes a service registration."""

    def __init__(
        self,
        service_type: type,
        implementation: type | None = None,
        factory: Callable | None = None,
        instance: Any | None = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT,
    ):
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime

    def validate(self) -> None:
        """Validate the service descriptor."""
        implementation_count = sum(
            [
                self.implementation is not None,
                self.factory is not None,
                self.instance is not None,
            ]
        )

        if implementation_count != 1:
            raise ValueError(
                f"Exactly one of implementation, factory, or instance must be provided "
                f"for service type {self.service_type.__name__}"
            )


class ServiceContainer:
    """Type-safe dependency injection container."""

    def __init__(self):
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, Any] = {}
        self._building: set[type] = set()  # Track circular dependencies

    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "ServiceContainer":
        """Register a transient service (new instance each time)."""
        return self._register_service(
            service_type, implementation, factory, LifetimeScope.TRANSIENT
        )

    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
    ) -> "ServiceContainer":
        """Register a singleton service (same instance each time)."""
        if instance is not None:
            self._singletons[service_type] = instance
            return self

        return self._register_service(
            service_type, implementation, factory, LifetimeScope.SINGLETON
        )

    def _register_service(
        self,
        service_type: type[T],
        implementation: type[T] | None = None,
        factory: Callable[[], T] | None = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT,
    ) -> "ServiceContainer":
        """Internal service registration method."""
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=implementation or service_type,
            factory=factory,
            lifetime=lifetime,
        )

        descriptor.validate()
        self._services[service_type] = descriptor
        return self

    def get(self, service_type: type[T]) -> T:
        """Resolve a service instance."""
        if service_type in self._building:
            raise ValueError(f"Circular dependency detected: {service_type.__name__}")

        # Check for existing singleton
        if service_type in self._singletons:
            return self._singletons[service_type]

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

            return instance

        finally:
            self._building.discard(service_type)

    def _create_instance(self, implementation_type: type[T]) -> T:
        """Create instance with constructor injection.

        This method can be used to create instances of classes that aren't registered
        in the container, as long as their dependencies are registered. It automatically
        resolves dependencies based on type hints.
        """
        if not hasattr(implementation_type, "__init__"):
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
            if param_name == "self":
                continue

            # Skip if parameter has a default value and is not a custom type
            if param.default != param.empty and not self._is_custom_type(
                type_hints.get(param_name)
            ):
                continue

            param_type = type_hints.get(param_name)
            if param_type and param_type != Any and self._is_custom_type(param_type):
                # Handle Optional[T] and Union types - provide None if not registered
                origin = get_origin(param_type)
                is_union = origin is Union or isinstance(param_type, types.UnionType)

                if is_union and type(None) in get_args(param_type):
                    # Optional type - try to get dependency, use None if not found
                    non_none_type = next(t for t in get_args(param_type) if t is not type(None))
                    if self.has(non_none_type):
                        kwargs[param_name] = self.get(non_none_type)
                    else:
                        kwargs[param_name] = None
                # Required dependency - try to get from container
                elif self.has(param_type):
                    kwargs[param_name] = self.get(param_type)
                else:
                    # Dependency not registered - this will cause an error when creating instance
                    # but allows polymorphic behavior where some handlers don't need all deps
                    type_name = self._get_type_name(param_type)
                    raise ValueError(
                        f"Required dependency {type_name} for {implementation_type.__name__}.{param_name} "
                        f"is not registered in the container"
                    )

        return implementation_type(**kwargs)

    def create_with_injection(self, class_type: type[T]) -> T:
        """Public method to create instances with automatic dependency injection.

        This is a convenience method for creating instances of classes that aren't
        registered in the container but need dependency injection. Useful for
        handlers and other transient objects.
        """
        return self._create_instance(class_type)

    def _get_type_name(self, param_type: type | Any) -> str:
        """Get a string representation of a type, handling Union types."""
        if param_type is None:
            return "None"

        # Handle Union types (both typing.Union and | syntax)
        origin = get_origin(param_type)
        if origin is Union or isinstance(param_type, types.UnionType):
            args = get_args(param_type)
            if args:
                arg_names = [self._get_type_name(arg) for arg in args]
                return " | ".join(arg_names)

        # Handle regular types with __name__
        if hasattr(param_type, "__name__"):
            return param_type.__name__

        # Fallback for types without __name__
        return str(param_type)

    def _is_custom_type(self, param_type: type | None) -> bool:
        """Check if a type is a custom class that should be injected."""
        if not param_type:
            return False

        # Skip built-in types
        builtin_types = (str, int, float, bool, list, dict, tuple, set)
        if param_type in builtin_types:
            return False

        # Skip typing module types and Union types
        from typing import Any, Union

        origin = get_origin(param_type)
        if origin is Union or isinstance(param_type, types.UnionType):
            # For Union types, check if any of the non-None args is a custom type
            args = get_args(param_type)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                return any(self._is_custom_type(arg) for arg in non_none_args)
            return False

        if param_type in (Union, Optional, Any, list, dict, tuple, set):
            return False

        # Check if it's a user-defined class
        return hasattr(param_type, "__module__") and not param_type.__module__.startswith("typing")

    def get_optional(self, service_type: type[T]) -> T | None:
        """Resolve a service instance, returning None if not registered."""
        try:
            return self.get(service_type)
        except ValueError:
            return None

    def has(self, service_type: type) -> bool:
        """Check if a service type is registered."""
        return service_type in self._services or service_type in self._singletons

    def clear(self) -> None:
        """Clear all services and singletons."""
        self._services.clear()
        self._singletons.clear()

    def register_instance(self, service_type: type[T], instance: T) -> "ServiceContainer":
        """Register a service instance as singleton.

        For ABC interfaces, uses issubclass check.
        For Protocols, validates if @runtime_checkable is used, otherwise skips check.
        """
        is_valid = False

        if hasattr(service_type, "__abstractmethods__"):
            is_valid = issubclass(type(instance), service_type)
        elif hasattr(service_type, "__protocol__"):
            if hasattr(service_type, "__runtime_checkable__"):
                try:
                    is_valid = isinstance(instance, service_type)
                except TypeError:
                    is_valid = True
            else:
                is_valid = True
        else:
            is_valid = isinstance(instance, service_type)

        if not is_valid:
            raise ValueError(
                f"Instance {type(instance).__name__} must be of type {service_type.__name__}"
            )

        descriptor = ServiceDescriptor(
            service_type=service_type,
            instance=instance,
            lifetime=LifetimeScope.SINGLETON,
        )
        self._services[service_type] = descriptor
        self._singletons[service_type] = instance
        return self

    def register_factory(
        self, service_type: type[T], factory: Callable[[], T]
    ) -> "ServiceContainer":
        """Register a factory for creating services."""
        if not callable(factory):
            error_msg = "Factory must be callable"
            raise TypeError(error_msg)

        descriptor = ServiceDescriptor(
            service_type=service_type, factory=factory, lifetime=LifetimeScope.TRANSIENT
        )
        self._services[service_type] = descriptor
        return self

    def validate_dependencies(self) -> None:
        """Validate that all registered dependencies can be resolved."""
        for service_type in self._services:
            try:
                self.get(service_type)
            except Exception as e:
                raise ValueError(
                    f"Dependency validation failed for {service_type.__name__}: {e}"
                ) from e


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
            if name.startswith("_") or obj.__module__ != module.__name__:
                continue

            # Find interfaces this class implements
            interfaces = [base for base in obj.__bases__ if hasattr(base, "__abstractmethods__")]

            if interfaces:
                interface = interfaces[0]
                container.register_singleton(interface, obj)
            else:
                container.register_singleton(obj, obj)

    except ImportError:
        pass
