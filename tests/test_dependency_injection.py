"""Comprehensive tests for the new dependency injection system."""

import pytest
from typing import Optional
from unittest.mock import Mock, MagicMock

from src.application.di_container import ServiceContainer, LifetimeScope
from src.core.interfaces import (
    IFileService,
)


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


class TestServiceContainer:
    """Test the new ServiceContainer implementation."""

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
        container.get(MockService)

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
            def __init__(self, service_b: "ServiceB"):
                self.service_b = service_b

        class ServiceB:
            def __init__(self, service_a: "ServiceA"):
                self.service_a = service_a

        container = ServiceContainer()
        container.register_transient(ServiceA)
        container.register_transient(ServiceB)

        # This should fail due to circular dependency
        try:
            container.get(ServiceA)
            assert False, "Should have raised circular dependency error"
        except ValueError as e:
            assert "Circular dependency" in str(e)


class TestRealInterfaces:
    """Test real interface implementations with DI container."""

    def test_real_download_service_interface(self):
        """Test real IDownloadService implementation."""
        from src.services.downloads import DownloadService

        # Create mock dependencies
        mock_service_factory = MagicMock()

        # Create service directly
        service = DownloadService(service_factory=mock_service_factory)

        assert isinstance(service, DownloadService)
        # Test that it has required methods (duck typing)
        assert hasattr(service, "get_downloads")
        assert hasattr(service, "add_download")
        assert hasattr(service, "remove_downloads")

    def test_real_file_service_interface(self):
        """Test real IFileService implementation."""
        from src.services.file import FileService

        container = ServiceContainer()
        container.register_singleton(IFileService, FileService)

        service = container.get(IFileService)
        assert isinstance(service, FileService)
        # Test that it implements key interface methods (duck typing)
        assert hasattr(service, "sanitize_filename")
        assert hasattr(service, "download_file")

    def test_real_message_queue_interface(self):
        """Test real IMessageQueue implementation."""
        from src.services.events.queue import MessageQueue

        # Create MessageQueue directly with mock status bar
        mock_status_bar = Mock()
        queue = MessageQueue(mock_status_bar)

        # Test that it implements the interface
        assert isinstance(queue, MessageQueue)
        assert hasattr(queue, "add_message")
        # Test that we can add a message
        queue.add_message("Test message")

    def test_real_download_handler_interface(self):
        """Test real IDownloadHandler implementation."""
        from src.handlers.download_handler import DownloadHandler

        # Create mock dependencies using MagicMock which has __name__
        mock_download_service = MagicMock()
        mock_service_factory = MagicMock()
        mock_file_service = MagicMock()
        mock_ui_state = MagicMock()

        # Create handler directly with mocks
        handler = DownloadHandler(
            download_service=mock_download_service,
            service_factory=mock_service_factory,
            file_service=mock_file_service,
            ui_state=mock_ui_state,
        )

        assert isinstance(handler, DownloadHandler)
        # Test that it has required methods
        assert hasattr(handler, "process_url")
        assert hasattr(handler, "handle_download_error")
        assert hasattr(handler, "is_available")

    def test_real_error_handler_interface(self):
        """Test real IErrorNotifier implementation."""
        # Skip due to complex GUI import chain - test ErrorHandler in coordinator tests
        # where proper GUI mocking is already set up
        import pytest

        pytest.skip(
            "ErrorHandler test moved to coordinator tests to avoid GUI import complexity"
        )


class TestIntegrationScenarios:
    """Test integration scenarios with multiple services."""

    def test_complex_dependency_graph(self):
        """Test a complex dependency graph."""

        class Database:
            def __init__(self):
                pass

        class Logger:
            def __init__(self):
                pass

        class UserService:
            def __init__(self, db: Database, logger: Logger):
                self.db = db
                self.logger = logger

        class AuthController:
            def __init__(self, user_service: UserService, logger: Logger):
                self.user_service = user_service
                self.logger = logger

        container = ServiceContainer()
        container.register_singleton(Database)
        container.register_singleton(Logger)
        container.register_singleton(UserService)
        container.register_singleton(AuthController)

        # Should be able to resolve the whole graph
        controller = container.get(AuthController)
        assert isinstance(controller, AuthController)
        assert isinstance(controller.user_service, UserService)
        assert isinstance(controller.user_service.db, Database)
        assert isinstance(controller.user_service.logger, Logger)
        assert isinstance(controller.logger, Logger)

        # Singletons should be the same instance
        assert controller.logger is controller.user_service.logger

    def test_mixed_lifetime_scopes(self):
        """Test mixing transient and singleton scopes."""

        class Config:
            def __init__(self):
                self.data = "config"

        class Service:
            def __init__(self, config: Config):
                self.config = config

        container = ServiceContainer()
        container.register_singleton(Config)
        container.register_transient(Service)

        # Multiple service instances should share the same config
        service1 = container.get(Service)
        service2 = container.get(Service)

        assert service1 is not service2  # Transient: different instances
        assert service1.config is service2.config  # Singleton: same config instance

    def test_optional_dependencies_resolution(self):
        """Test resolution of optional dependencies."""

        class Config:
            def __init__(self):
                self.settings = {}

        class OptionalService:
            def __init__(
                self, required: str = "test", optional: Optional[Config] = None
            ):
                self.required = required
                self.optional = optional

        container = ServiceContainer()
        container.register_transient(OptionalService)

        # Should work without optional dependency registered
        service = container.get(OptionalService)
        assert service.required == "test"  # Default value
        assert service.optional is None

    def test_factory_registration(self):
        """Test factory registration with dependencies."""

        class Service:
            def __init__(self, value: int):
                self.value = value

        def create_service() -> Service:
            return Service(42)

        container = ServiceContainer()
        container.register_factory(Service, create_service)

        service = container.get(Service)
        assert isinstance(service, Service)
        assert service.value == 42


if __name__ == "__main__":
    pytest.main([__file__])
