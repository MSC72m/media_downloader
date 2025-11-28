"""Test utility functions."""


def test_logger():
    """Test logger functionality."""
    from utils.logger import get_logger

    logger = get_logger("test")
    assert logger.name == "test"

    # Test that logger methods exist
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
    assert hasattr(logger, "debug")


def test_common_utils():
    """Test common utility functions."""
    from utils.common import sanitize_filename

    # Test filename sanitization
    result = sanitize_filename("test<>file|name")
    assert "<" not in result
    assert ">" not in result
    assert "|" not in result

    # Test with normal filename
    result = sanitize_filename("normal_file_name")
    assert result == "normal_file_name"

    # Test with empty string
    result = sanitize_filename("")
    assert result == ""


def test_window_utils():
    """Test window utility functions."""
    from utils.window import WindowCenterMixin

    # Test that the mixin exists
    assert WindowCenterMixin is not None
