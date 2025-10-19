"""Tests for base classes."""

import pytest
from core.base import BaseDownloader, NetworkError, AuthenticationError, ServiceError


class TestBaseDownloader:
    """Test BaseDownloader."""

    def test_base_downloader_creation(self):
        """Test BaseDownloader can be created."""
        downloader = BaseDownloader()
        assert downloader is not None

    def test_base_downloader_methods(self):
        """Test BaseDownloader has expected methods."""
        downloader = BaseDownloader()
        
        # Check that expected methods exist
        assert hasattr(downloader, 'download')
        assert hasattr(downloader, 'get_metadata')


class TestNetworkError:
    """Test NetworkError exception."""

    def test_network_error_creation(self):
        """Test NetworkError can be created."""
        error = NetworkError("Network connection failed")
        assert str(error) == "Network connection failed"

    def test_network_error_inheritance(self):
        """Test NetworkError inherits from Exception."""
        error = NetworkError("Test error")
        assert isinstance(error, Exception)


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_creation(self):
        """Test AuthenticationError can be created."""
        error = AuthenticationError("Authentication failed")
        assert str(error) == "Authentication failed"

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inherits from Exception."""
        error = AuthenticationError("Test error")
        assert isinstance(error, Exception)


class TestServiceError:
    """Test ServiceError exception."""

    def test_service_error_creation(self):
        """Test ServiceError can be created."""
        error = ServiceError("Service unavailable")
        assert str(error) == "Service unavailable"

    def test_service_error_inheritance(self):
        """Test ServiceError inherits from Exception."""
        error = ServiceError("Test error")
        assert isinstance(error, Exception)
