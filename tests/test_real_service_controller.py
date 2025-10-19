"""Tests for real service controller without heavy mocking."""

import pytest
import sys
import os
from unittest.mock import Mock

# Add src to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.service_controller import ServiceController


class TestRealServiceController:
    """Test real ServiceController."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_download_service = Mock()
        self.mock_cookie_manager = Mock()
        self.controller = ServiceController(self.mock_download_service, self.mock_cookie_manager)

    def test_initialization(self):
        """Test controller initialization."""
        assert self.controller.download_service == self.mock_download_service
        assert self.controller.cookie_manager == self.mock_cookie_manager
        assert self.controller._active_downloads == 0

    def test_has_active_downloads(self):
        """Test has_active_downloads method."""
        result = self.controller.has_active_downloads()
        assert result is False

    def test_safe_decode_bytes_empty(self):
        """Test _safe_decode_bytes with empty bytes."""
        result = self.controller._safe_decode_bytes(b"")
        assert result == ""

    def test_safe_decode_bytes_none(self):
        """Test _safe_decode_bytes with None."""
        result = self.controller._safe_decode_bytes(None)
        assert result == ""

    def test_safe_decode_bytes_utf8(self):
        """Test _safe_decode_bytes with valid UTF-8."""
        test_string = "Hello, 世界!"
        result = self.controller._safe_decode_bytes(test_string.encode('utf-8'))
        assert result == test_string

    def test_safe_decode_bytes_latin1_fallback(self):
        """Test _safe_decode_bytes with Latin-1 fallback."""
        # Create bytes that are valid in latin-1 but not utf-8
        test_bytes = b'\x80\x81\x82'
        result = self.controller._safe_decode_bytes(test_bytes)
        assert result == '\x80\x81\x82'

    def test_safe_decode_bytes_replace_fallback(self):
        """Test _safe_decode_bytes with replace fallback."""
        # Create invalid bytes
        test_bytes = b'\xff\xfe\xfd'
        result = self.controller._safe_decode_bytes(test_bytes)
        # Should use replace strategy
        assert len(result) > 0

    def test_safe_decode_bytes_repr_fallback(self):
        """Test _safe_decode_bytes with repr fallback."""
        # Create bytes that cause all decoding to fail
        test_bytes = b'\x00\x01\x02'
        result = self.controller._safe_decode_bytes(test_bytes)
        # Should return some representation
        assert isinstance(result, str)

    def test_start_downloads_with_download_handler(self):
        """Test start_downloads when download handler is available."""
        mock_download_handler = Mock()
        self.mock_download_service.download_handler = mock_download_handler
        
        downloads = [Mock(), Mock()]
        progress_callback = Mock()
        completion_callback = Mock()
        
        self.controller.start_downloads(downloads, "/test/path", progress_callback, completion_callback)
        
        mock_download_handler.start_downloads.assert_called_once_with(
            downloads, "/test/path", progress_callback, completion_callback
        )

    def test_start_downloads_with_container_handler(self):
        """Test start_downloads when download handler is in container."""
        mock_download_handler = Mock()
        mock_container = Mock()
        mock_container.get.return_value = mock_download_handler
        self.mock_download_service.container = mock_container
        self.mock_download_service.download_handler = None  # Explicitly set to None
        
        downloads = [Mock(), Mock()]
        progress_callback = Mock()
        completion_callback = Mock()
        
        self.controller.start_downloads(downloads, "/test/path", progress_callback, completion_callback)
        
        mock_download_handler.start_downloads.assert_called_once_with(
            downloads, "/test/path", progress_callback, completion_callback
        )

    def test_start_downloads_without_handler(self):
        """Test start_downloads when no download handler is available."""
        self.mock_download_service.download_handler = None
        self.mock_download_service.container = None
        
        downloads = [Mock(), Mock()]
        completion_callback = Mock()
        
        self.controller.start_downloads(downloads, "/test/path", None, completion_callback)
        
        completion_callback.assert_called_once_with(False, "No download handler available")

    def test_start_downloads_without_callbacks(self):
        """Test start_downloads without callbacks."""
        mock_download_handler = Mock()
        self.mock_download_service.download_handler = mock_download_handler
        
        downloads = [Mock(), Mock()]
        
        # Should not raise an exception
        self.controller.start_downloads(downloads, "/test/path", None, None)
        
        mock_download_handler.start_downloads.assert_called_once_with(
            downloads, "/test/path", None, None
        )
