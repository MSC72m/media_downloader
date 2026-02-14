import importlib
import inspect
import types
from collections.abc import Callable
from enum import Enum, auto
from inspect import signature
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

T = TypeVar("T")


class LifetimeScope(Enum):
    SINGLETON = auto()
    TRANSIENT = auto()


class ServiceDescriptor:
    def __init__(
        self,
        service_type: type,
        implementation: type | None = None,
        factory: Callable | None = None,
        instance: object | None = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT,
    ) -> None:
        self.service_type = service_type
        self.implementation = implementation
        self.factory = factory
        self.instance = instance
        self.lifetime = lifetime

    def validate(self) -> None:
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
    def __init__(self) -> None:
        self._services: dict[type, ServiceDescriptor] = {}
        self._singletons: dict[type, object] = {}
        self._building: set[type] = set()

    def register_transient(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[[], T] | None = None,
        factory: Callable[[], T] | None = None,
    ) -> "ServiceContainer":
        return self._register_service(
            service_type, implementation, factory, LifetimeScope.TRANSIENT
        )

    def register_singleton(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[[], T] | None = None,
        factory: Callable[[], T] | None = None,
        instance: T | None = None,
    ) -> "ServiceContainer":
        if instance is not None:
            self._singletons[service_type] = instance
            return self

        return self._register_service(
            service_type, implementation, factory, LifetimeScope.SINGLETON
        )

    def _register_service(
        self,
        service_type: type[T],
        implementation: type[T] | Callable[[], T] | None = None,
        factory: Callable[[], T] | None = None,
        lifetime: LifetimeScope = LifetimeScope.TRANSIENT,
    ) -> "ServiceContainer":
        if implementation is not None and factory is None and not isinstance(implementation, type):
            factory = cast(Callable[[], T], implementation)
            implementation = None

        resolved_implementation: type | None
        if isinstance(implementation, type):
            resolved_implementation = implementation
        elif factory is not None:
            resolved_implementation = None
        else:
            resolved_implementation = service_type
        descriptor = ServiceDescriptor(
            service_type=service_type,
            implementation=resolved_implementation,
            factory=factory,
            lifetime=lifetime,
        )

        descriptor.validate()
        self._services[service_type] = descriptor
        return self

    def get(self, service_type: type[T]) -> T:
        if service_type in self._building:
            raise ValueError(f"Circular dependency detected: {service_type.__name__}")

        if service_type in self._singletons:
            return cast(T, self._singletons[service_type])

        if service_type not in self._services:
            raise ValueError(f"Service not registered: {service_type.__name__}")

        descriptor = self._services[service_type]

        if descriptor.instance is not None:
            return cast(T, descriptor.instance)

        self._building.add(service_type)

        try:
            if descriptor.factory:
                instance = descriptor.factory()
            else:
                if descriptor.implementation is None:
                    error_msg = f"No implementation registered for service: {service_type.__name__}"
                    raise ValueError(error_msg)
                instance = self._create_instance(descriptor.implementation)

            if descriptor.lifetime == LifetimeScope.SINGLETON:
                self._singletons[service_type] = instance

            return cast(T, instance)

        finally:
            self._building.discard(service_type)

    def _create_instance(self, implementation_type: type[T]) -> T:
        if not hasattr(implementation_type, "__init__"):
            return implementation_type()

        sig = signature(implementation_type.__init__)

        global_ns = {}
        class_name = implementation_type.__name__
        global_ns[class_name] = implementation_type

        for service_type in self._services:
            global_ns[service_type.__name__] = service_type

        type_hints = get_type_hints(implementation_type.__init__, globalns=global_ns)

        kwargs = {}
        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            if param.default != param.empty and not self._is_custom_type(
                type_hints.get(param_name)
            ):
                continue

            if (
                (param_type := type_hints.get(param_name))
                and param_type != Any
                and self._is_custom_type(param_type)
            ):
                origin = get_origin(param_type)
                is_union = origin is Union or isinstance(param_type, types.UnionType)

                if is_union and type(None) in get_args(param_type):
                    non_none_type = next(t for t in get_args(param_type) if t is not type(None))
                    dependency_type = cast(type, non_none_type)
                    if self.has(dependency_type):
                        kwargs[param_name] = self.get(dependency_type)
                    else:
                        kwargs[param_name] = None
                elif isinstance(param_type, type) and self.has(param_type):
                    kwargs[param_name] = self.get(param_type)
                else:
                    type_name = self._get_type_name(param_type)
                    raise ValueError(
                        f"Required dependency {type_name} for {implementation_type.__name__}.{param_name} "
                        f"is not registered in the container"
                    )

        return implementation_type(**kwargs)

    def create_with_injection(self, class_type: type[T]) -> T:
        return self._create_instance(class_type)

    def _get_type_name(self, param_type: type | object) -> str:
        if param_type is None:
            return "None"

        origin = get_origin(param_type)
        if (origin is Union or isinstance(param_type, types.UnionType)) and (
            args := get_args(param_type)
        ):
            arg_names = [self._get_type_name(arg) for arg in args]
            return " | ".join(arg_names)

        if type_name := getattr(param_type, "__name__", None):
            return str(type_name)

        return str(param_type)

    def _is_custom_type(self, param_type: type | None) -> bool:
        if not param_type:
            return False

        builtin_types = (str, int, float, bool, list, dict, tuple, set, object)
        if param_type in builtin_types:
            return False

        if get_origin(param_type) is Union or isinstance(param_type, types.UnionType):
            args = get_args(param_type)
            if non_none_args := [arg for arg in args if arg is not type(None)]:
                return any(self._is_custom_type(arg) for arg in non_none_args)
            return False

        if param_type in (Union, Any, list, dict, tuple, set):
            return False

        return hasattr(param_type, "__module__") and not param_type.__module__.startswith("typing")

    def get_optional(self, service_type: type[T]) -> T | None:
        try:
            return self.get(service_type)
        except ValueError:
            return None

    def has(self, service_type: type) -> bool:
        return service_type in self._services or service_type in self._singletons

    def clear(self) -> None:
        self._services.clear()
        self._singletons.clear()

    def register_instance(self, service_type: type[T], instance: T) -> "ServiceContainer":
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
            service_type_name = getattr(service_type, "__name__", str(service_type))
            instance_type_name = type(instance).__name__
            raise ValueError(f"Instance {instance_type_name} must be of type {service_type_name}")

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
        if not callable(factory):
            error_msg = "Factory must be callable"
            raise TypeError(error_msg)

        descriptor = ServiceDescriptor(
            service_type=service_type, factory=factory, lifetime=LifetimeScope.TRANSIENT
        )
        self._services[service_type] = descriptor
        return self

    def validate_dependencies(self) -> None:
        for service_type in self._services:
            try:
                self.get(service_type)
            except Exception as e:
                raise ValueError(
                    f"Dependency validation failed for {service_type.__name__}: {e}"
                ) from e


def auto_register_by_convention(container: ServiceContainer, module_path: str) -> None:
    try:
        module = importlib.import_module(module_path)

        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.startswith("_") or obj.__module__ != module.__name__:
                continue

            if interfaces := [
                base for base in obj.__bases__ if hasattr(base, "__abstractmethods__")
            ]:
                interface = interfaces[0]
                container.register_singleton(interface, obj)
            else:
                container.register_singleton(obj, obj)

    except ImportError:
        pass
