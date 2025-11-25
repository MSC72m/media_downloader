"""Core DI system tests without heavy dependencies."""

import pytest
from typing import Optional

# Import just the core DI system
from src.core.application.di_container import ServiceContainer, LifetimeScope


class MockService:
    """Mock service for testing."""

    def __init__(self, name: str = "test"):
        self.name = name
        self.initialized = False

    def initialize(self):
        self.initialized = True


class MockServiceWithDeps:
    """Mock service with dependencies."""

    def __init__(self, dependency: MockService):
        self.dependency = dependency
        self.initialized = False

    def initialize(self):
        self.initialized = True


class TestServiceContainerCore:
    """Test the core ServiceContainer functionality."""

    def test_container_creation(self):
        """Test container can be created."""
        container = ServiceContainer()
        assert container is not None
        assert len(container._services) == 0
        assert len(container._singletons) == 0

    def test_register_transient(self):
        """Test transient service registration."""
        container = ServiceContainer()
        container.register_transient(MockService)

        assert MockService in container._services
        descriptor = container._services[MockService]
        assert descriptor.lifetime == LifetimeScope.TRANSIENT
        assert descriptor.implementation == MockService

    def test_register_singleton(self):
        """Test singleton service registration."""
        container = ServiceContainer()
        container.register_singleton(MockService)

        assert MockService in container._services
        descriptor = container._services[MockService]
        assert descriptor.lifetime == LifetimeScope.SINGLETON
        assert descriptor.implementation == MockService

    def test_register_singleton_with_instance(self):
        """Test singleton registration with instance."""
        container = ServiceContainer()
        instance = MockService("instance")
        container.register_singleton(MockService, instance=instance)

        assert MockService in container._singletons
        assert container._singletons[MockService] is instance

    def test_resolve_transient(self):
        """Test transient service resolution creates new instances."""
        container = ServiceContainer()
        container.register_transient(MockService)

        instance1 = container.get(MockService)
        instance2 = container.get(MockService)

        assert instance1 is not instance2
        assert isinstance(instance1, MockService)
        assert isinstance(instance2, MockService)

    def test_resolve_singleton(self):
        """Test singleton service resolution returns same instance."""
        container = ServiceContainer()
        container.register_singleton(MockService)

        instance1 = container.get(MockService)
        instance2 = container.get(MockService)

        assert instance1 is instance2
        assert isinstance(instance1, MockService)

    def test_resolve_with_dependencies(self):
        """Test service resolution with constructor injection."""
        container = ServiceContainer()
        container.register_transient(MockService)
        container.register_transient(MockServiceWithDeps)

        service = container.get(MockServiceWithDeps)

        assert isinstance(service, MockServiceWithDeps)
        assert isinstance(service.dependency, MockService)

    def test_resolve_optional_dependency(self):
        """Test service resolution with optional dependency."""

        class ServiceWithOptional:
            def __init__(self, dependency: Optional[MockService] = None):
                self.dependency = dependency

        container = ServiceContainer()
        container.register_transient(ServiceWithOptional)

        service = container.get(ServiceWithOptional)
        assert service.dependency is None

    def test_has_service(self):
        """Test service existence checking."""
        container = ServiceContainer()

        assert not container.has(MockService)

        container.register_singleton(MockService)
        assert container.has(MockService)

    def test_get_optional(self):
        """Test optional service resolution."""
        container = ServiceContainer()

        # Service not registered
        service = container.get_optional(MockService)
        assert service is None

        # Service registered
        container.register_singleton(MockService)
        service = container.get_optional(MockService)
        assert isinstance(service, MockService)

    def test_clear(self):
        """Test container clearing."""
        container = ServiceContainer()
        container.register_singleton(MockService)
        instance = container.get(MockService)

        assert len(container._services) > 0
        assert len(container._singletons) > 0

        container.clear()

        assert len(container._services) == 0
        assert len(container._singletons) == 0

    def test_validate_dependencies_success(self):
        """Test dependency validation with valid dependencies."""
        container = ServiceContainer()
        container.register_transient(MockService)
        container.register_transient(MockServiceWithDeps)

        # Should not raise exception
        container.validate_dependencies()

    def test_validate_dependencies_failure(self):
        """Test dependency validation with missing dependencies."""

        class ServiceWithMissingDeps:
            def __init__(self, dependency: MockService):  # MockService not registered
                self.dependency = dependency

        container = ServiceContainer()
        container.register_transient(ServiceWithMissingDeps)

        with pytest.raises(ValueError, match="Dependency validation failed"):
            container.validate_dependencies()

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""

        class ServiceA:
            def __init__(self, service_b: 'ServiceB'):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a: ServiceA):
                self.service_a = service_a

        container = ServiceContainer()
        container.register_transient(ServiceA)
        container.register_transient(ServiceB)

        with pytest.raises(ValueError, match="Circular dependency detected"):
            container.get(ServiceA)


class TestLazyImports:
    """Test that lazy imports work correctly."""

    def test_core_lazy_imports(self):
        """Test core lazy imports work."""
        from src.core import get_service_container, get_application_orchestrator

        ServiceContainer = get_service_container()
        assert ServiceContainer is not None
        assert callable(ServiceContainer)

        Orchestrator = get_application_orchestrator()
        assert Orchestrator is not None
        assert callable(Orchestrator)

    def test_application_lazy_imports(self):
        """Test application lazy imports work."""
        from src.core.application import get_orchestrator

        Orchestrator = get_orchestrator()
        assert Orchestrator is not None
        assert callable(Orchestrator)


if __name__ == "__main__":
    pytest.main([__file__])