"""Comprehensive tests for base classes to achieve 100% coverage."""

import pytest
from core.base import BaseDownloader, NetworkError, AuthenticationError, ServiceError


class TestBaseDownloaderComprehensive:
    """Comprehensive tests for BaseDownloader."""

    def test_base_downloader_abstract_class(self):
        """Test BaseDownloader is abstract and cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseDownloader()

    def test_base_downloader_methods_exist(self):
        """Test BaseDownloader has expected methods."""
        # Check that expected methods exist on the class
        assert hasattr(BaseDownloader, 'download')
        # Note: get_metadata is not defined in the actual BaseDownloader class

    def test_base_downloader_download_method_signature(self):
        """Test BaseDownloader download method signature."""
        # Check that the method exists and is abstract
        assert hasattr(BaseDownloader, 'download')
        # The method should be abstract
        assert getattr(BaseDownloader.download, '__isabstractmethod__', False)

    def test_base_downloader_inheritance_works(self):
        """Test that concrete implementations can inherit from BaseDownloader."""
        class ConcreteDownloader(BaseDownloader):
            def download(self, url, save_path, progress_callback=None):
                return True
        
        downloader = ConcreteDownloader()
        assert isinstance(downloader, BaseDownloader)
        assert downloader.download("test", "test") is True

    def test_base_downloader_inheritance(self):
        """Test BaseDownloader inheritance."""
        class TestDownloader(BaseDownloader):
            def download(self, url, path):
                return True
            
            def get_metadata(self, url):
                return {"title": "Test"}
        
        downloader = TestDownloader()
        assert isinstance(downloader, BaseDownloader)
        assert downloader.download("test", "test") is True
        assert downloader.get_metadata("test") == {"title": "Test"}


class TestNetworkErrorComprehensive:
    """Comprehensive tests for NetworkError exception."""

    def test_network_error_creation_with_message(self):
        """Test NetworkError can be created with message."""
        error = NetworkError("Network connection failed")
        assert str(error) == "Network connection failed"

    def test_network_error_creation_without_message(self):
        """Test NetworkError requires message parameter."""
        with pytest.raises(TypeError):
            NetworkError()

    def test_network_error_creation_with_empty_message(self):
        """Test NetworkError can be created with empty message."""
        error = NetworkError("")
        assert str(error) == ""

    def test_network_error_creation_with_unicode_message(self):
        """Test NetworkError can be created with unicode message."""
        error = NetworkError("网络连接失败 🌍")
        assert str(error) == "网络连接失败 🌍"

    def test_network_error_inheritance(self):
        """Test NetworkError inherits from Exception."""
        error = NetworkError("Test error")
        assert isinstance(error, Exception)

    def test_network_error_raising(self):
        """Test NetworkError can be raised."""
        with pytest.raises(NetworkError) as exc_info:
            raise NetworkError("Test network error")
        
        assert str(exc_info.value) == "Test network error"

    def test_network_error_catching(self):
        """Test NetworkError can be caught."""
        try:
            raise NetworkError("Test error")
        except NetworkError as e:
            assert str(e) == "Test error"
        except Exception:
            pytest.fail("NetworkError should be caught by NetworkError handler")


class TestAuthenticationErrorComprehensive:
    """Comprehensive tests for AuthenticationError exception."""

    def test_authentication_error_creation_with_message(self):
        """Test AuthenticationError can be created with message."""
        error = AuthenticationError("Authentication failed")
        assert str(error) == "Authentication failed"

    def test_authentication_error_creation_without_message(self):
        """Test AuthenticationError requires message parameter."""
        with pytest.raises(TypeError):
            AuthenticationError()

    def test_authentication_error_creation_with_empty_message(self):
        """Test AuthenticationError can be created with empty message."""
        error = AuthenticationError("")
        assert str(error) == ""

    def test_authentication_error_creation_with_unicode_message(self):
        """Test AuthenticationError can be created with unicode message."""
        error = AuthenticationError("认证失败 🔐")
        assert str(error) == "认证失败 🔐"

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inherits from Exception."""
        error = AuthenticationError("Test error")
        assert isinstance(error, Exception)

    def test_authentication_error_raising(self):
        """Test AuthenticationError can be raised."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Test auth error")
        
        assert str(exc_info.value) == "Test auth error"

    def test_authentication_error_catching(self):
        """Test AuthenticationError can be caught."""
        try:
            raise AuthenticationError("Test error")
        except AuthenticationError as e:
            assert str(e) == "Test error"
        except Exception:
            pytest.fail("AuthenticationError should be caught by AuthenticationError handler")


class TestServiceErrorComprehensive:
    """Comprehensive tests for ServiceError exception."""

    def test_service_error_creation_with_message(self):
        """Test ServiceError can be created with message."""
        error = ServiceError("Service unavailable")
        assert str(error) == "Service unavailable"

    def test_service_error_creation_without_message(self):
        """Test ServiceError requires message parameter."""
        with pytest.raises(TypeError):
            ServiceError()

    def test_service_error_creation_with_empty_message(self):
        """Test ServiceError can be created with empty message."""
        error = ServiceError("")
        assert str(error) == ""

    def test_service_error_creation_with_unicode_message(self):
        """Test ServiceError can be created with unicode message."""
        error = ServiceError("服务不可用 🚫")
        assert str(error) == "服务不可用 🚫"

    def test_service_error_inheritance(self):
        """Test ServiceError inherits from Exception."""
        error = ServiceError("Test error")
        assert isinstance(error, Exception)

    def test_service_error_raising(self):
        """Test ServiceError can be raised."""
        with pytest.raises(ServiceError) as exc_info:
            raise ServiceError("Test service error")
        
        assert str(exc_info.value) == "Test service error"

    def test_service_error_catching(self):
        """Test ServiceError can be caught."""
        try:
            raise ServiceError("Test error")
        except ServiceError as e:
            assert str(e) == "Test error"
        except Exception:
            pytest.fail("ServiceError should be caught by ServiceError handler")


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_exception(self):
        """Test all custom exceptions inherit from Exception."""
        assert issubclass(NetworkError, Exception)
        assert issubclass(AuthenticationError, Exception)
        assert issubclass(ServiceError, Exception)

    def test_exceptions_are_different_types(self):
        """Test that exceptions are different types."""
        assert NetworkError is not AuthenticationError
        assert NetworkError is not ServiceError
        assert AuthenticationError is not ServiceError

    def test_exception_instances_are_different(self):
        """Test that exception instances are different."""
        network_error = NetworkError("Network error")
        auth_error = AuthenticationError("Auth error")
        service_error = ServiceError("Service error")
        
        assert network_error is not auth_error
        assert network_error is not service_error
        assert auth_error is not service_error

    def test_exception_catching_hierarchy(self):
        """Test exception catching hierarchy."""
        # Test that specific exceptions can be caught by their specific handlers
        with pytest.raises(NetworkError):
            raise NetworkError("Network error")
        
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Auth error")
        
        with pytest.raises(ServiceError):
            raise ServiceError("Service error")
        
        # Test that all can be caught by Exception handler
        with pytest.raises(Exception):
            raise NetworkError("Network error")
        
        with pytest.raises(Exception):
            raise AuthenticationError("Auth error")
        
        with pytest.raises(Exception):
            raise ServiceError("Service error")
