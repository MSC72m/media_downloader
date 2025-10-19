"""Comprehensive tests for service container to achieve 100% coverage."""

import pytest
from core.container import ServiceContainer


class TestServiceContainerComprehensive:
    """Comprehensive tests for ServiceContainer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.container = ServiceContainer()

    def test_initialization(self):
        """Test container initialization."""
        assert self.container is not None
        assert hasattr(self.container, '_services')

    def test_register_and_get_single_service(self):
        """Test registering and retrieving a single service."""
        test_service = "test_service_instance"
        
        # Register service
        self.container.register("test_key", test_service)
        
        # Retrieve service
        retrieved = self.container.get("test_key")
        assert retrieved == test_service

    def test_register_and_get_multiple_services(self):
        """Test registering and retrieving multiple services."""
        service1 = "service1"
        service2 = "service2"
        service3 = "service3"
        
        self.container.register("key1", service1)
        self.container.register("key2", service2)
        self.container.register("key3", service3)
        
        assert self.container.get("key1") == service1
        assert self.container.get("key2") == service2
        assert self.container.get("key3") == service3

    def test_get_nonexistent_key(self):
        """Test getting a non-existent key."""
        result = self.container.get("nonexistent_key")
        assert result is None

    def test_get_empty_key(self):
        """Test getting an empty key."""
        result = self.container.get("")
        assert result is None

    def test_get_none_key(self):
        """Test getting None as key."""
        result = self.container.get(None)
        assert result is None

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

    def test_register_empty_string_value(self):
        """Test registering empty string value."""
        self.container.register("empty_key", "")
        result = self.container.get("empty_key")
        assert result == ""

    def test_register_zero_value(self):
        """Test registering zero value."""
        self.container.register("zero_key", 0)
        result = self.container.get("zero_key")
        assert result == 0

    def test_register_false_value(self):
        """Test registering False value."""
        self.container.register("false_key", False)
        result = self.container.get("false_key")
        assert result is False

    def test_register_list_value(self):
        """Test registering list value."""
        test_list = [1, 2, 3, "test"]
        self.container.register("list_key", test_list)
        result = self.container.get("list_key")
        assert result == test_list

    def test_register_dict_value(self):
        """Test registering dict value."""
        test_dict = {"key1": "value1", "key2": "value2"}
        self.container.register("dict_key", test_dict)
        result = self.container.get("dict_key")
        assert result == test_dict

    def test_register_object_value(self):
        """Test registering object value."""
        class TestObject:
            def __init__(self):
                self.value = "test"
        
        test_obj = TestObject()
        self.container.register("obj_key", test_obj)
        result = self.container.get("obj_key")
        assert result == test_obj
        assert result.value == "test"

    def test_register_with_special_characters_in_key(self):
        """Test registering with special characters in key."""
        special_key = "key-with-special_chars.123"
        test_service = "special_service"
        
        self.container.register(special_key, test_service)
        result = self.container.get(special_key)
        assert result == test_service

    def test_register_with_unicode_key(self):
        """Test registering with unicode key."""
        unicode_key = "key_世界_🌍"
        test_service = "unicode_service"
        
        self.container.register(unicode_key, test_service)
        result = self.container.get(unicode_key)
        assert result == test_service

    def test_register_with_numeric_key(self):
        """Test registering with numeric key."""
        numeric_key = 12345
        test_service = "numeric_service"
        
        self.container.register(numeric_key, test_service)
        result = self.container.get(numeric_key)
        assert result == test_service

    def test_register_with_tuple_key(self):
        """Test registering with tuple key."""
        tuple_key = ("key1", "key2", "key3")
        test_service = "tuple_service"
        
        self.container.register(tuple_key, test_service)
        result = self.container.get(tuple_key)
        assert result == test_service

    def test_register_with_none_key(self):
        """Test registering with None key."""
        test_service = "none_key_service"
        
        self.container.register(None, test_service)
        result = self.container.get(None)
        assert result == test_service

    def test_register_with_empty_string_key(self):
        """Test registering with empty string key."""
        test_service = "empty_string_service"
        
        self.container.register("", test_service)
        result = self.container.get("")
        assert result == test_service

    def test_register_large_number_of_services(self):
        """Test registering a large number of services."""
        services = {}
        for i in range(1000):
            key = f"service_{i}"
            value = f"value_{i}"
            services[key] = value
            self.container.register(key, value)
        
        # Verify all services can be retrieved
        for key, expected_value in services.items():
            result = self.container.get(key)
            assert result == expected_value

    def test_register_and_get_with_whitespace_keys(self):
        """Test registering and getting with whitespace keys."""
        whitespace_keys = [" ", "  ", "\t", "\n", " \t\n "]
        
        for i, key in enumerate(whitespace_keys):
            value = f"whitespace_value_{i}"
            self.container.register(key, value)
            result = self.container.get(key)
            assert result == value
