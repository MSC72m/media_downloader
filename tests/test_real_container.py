"""Tests for real service container without heavy mocking."""

import sys
import os

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.container import ServiceContainer


class TestRealServiceContainer:
    """Test real ServiceContainer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = ServiceContainer()

    def test_initialization(self):
        """Test container initialization."""
        assert self.container is not None

    def test_register_and_get(self):
        """Test registering and retrieving services."""
        test_service = "test_service_instance"
        
        # Register service
        self.container.register("test_key", test_service)
        
        # Retrieve service
        retrieved = self.container.get("test_key")
        assert retrieved == test_service

    def test_get_nonexistent_key(self):
        """Test getting a non-existent key."""
        result = self.container.get("nonexistent_key")
        assert result is None

    def test_register_multiple_services(self):
        """Test registering multiple services."""
        service1 = "service1"
        service2 = "service2"
        
        self.container.register("key1", service1)
        self.container.register("key2", service2)
        
        assert self.container.get("key1") == service1
        assert self.container.get("key2") == service2

    def test_register_overwrite(self):
        """Test overwriting an existing service."""
        original_service = "original"
        new_service = "new"
        
        self.container.register("key", original_service)
        assert self.container.get("key") == original_service
        
        self.container.register("key", new_service)
        assert self.container.get("key") == new_service

    def test_register_none_value(self):
        """Test registering None value."""
        self.container.register("none_key", None)
        result = self.container.get("none_key")
        assert result is None
