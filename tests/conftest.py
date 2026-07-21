"""Pytest configuration and mocking for testing without GUI dependencies."""

import os
import shutil
import socket
import sys
import tempfile
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Early check: --run-network in CLI args.
# This MUST run before any sys.modules mocking because it controls
# whether network dependencies (requests, yt-dlp, instaloader) are mocked.
_RUN_NETWORK = "--run-network" in sys.argv

# ================================
# MOCK CLASSES - Define early before use
# ================================


class MockTk:
    """Mock tkinter base class."""

    def __init__(self, *args, **kwargs) -> None:
        pass


class MockTkWidget:
    """Mock tkinter widget base class."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def pack(self, **kwargs) -> None:
        pass

    def grid(self, **kwargs) -> None:
        pass

    def place(self, **kwargs) -> None:
        pass

    def configure(self, **kwargs) -> None:
        pass

    def cget(self, *args) -> None:
        return None

    def bind(self, *args, **kwargs) -> None:
        return None


class MockTkFrame(MockTkWidget):
    pass


class MockTkLabel(MockTkWidget):
    pass


class MockTkButton(MockTkWidget):
    pass


class MockTkEntry(MockTkWidget):
    pass


class MockTkListbox(MockTkWidget):
    pass


class MockCTk:
    """Mock customtkinter base class."""

    def __init__(self, *args, **kwargs) -> None:
        pass


class MockTkWidget2:
    """Mock customtkinter widget base class."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def pack(self, **kwargs) -> None:
        pass

    def grid(self, **kwargs) -> None:
        pass

    def place(self, **kwargs) -> None:
        pass

    def configure(self, **kwargs) -> None:
        pass

    def cget(self, *args) -> None:
        return None

    def bind(self, *args, **kwargs) -> None:
        return None


class MockMessagebox:
    """Mock messagebox functions."""

    def showerror(self, title, message) -> None:
        pass

    def showwarning(self, title, message) -> None:
        pass

    def showinfo(self, title, message) -> None:
        pass


class MockFiledialog:
    """Mock file dialog functions."""

    def askopenfilename(self, **kwargs) -> str:
        return ""

    def askdirectory(self, **kwargs) -> str:
        return ""


class MockBaseModel:
    """Mock Pydantic BaseModel."""

    def __init__(self, **kwargs) -> None:
        # Get default values from class attributes that are MockField objects
        for key, value in self.__class__.__dict__.items():
            if not key.startswith("_") and hasattr(value, "value") and key not in kwargs:
                setattr(self, key, value.value)

        # Set provided kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockField:
    """Mock Pydantic Field."""

    def __init__(self, default=None, default_factory=None, description=None, **kwargs) -> None:
        # Store the actual value that should be returned when the field is accessed
        resolved_value = (
            default_factory()
            if default_factory is not None and callable(default_factory)
            else default_factory
            if default_factory is not None
            else default
        )
        self.value: Any = resolved_value
        self.default = default
        self.default_factory = default_factory
        self.description = description

    def __str__(self) -> str:
        """Return the default value as string representation."""
        return str(self.value) if self.value is not None else ""

    def __repr__(self) -> str:
        """Return the default value as representation."""
        return repr(self.value)

    def __eq__(self, other):
        """Compare the default value with other."""
        return self.value == other

    def __lt__(self, other):
        """Less than comparison with default value."""
        return self.value < other if self.value is not None else False

    def __le__(self, other):
        """Less than or equal comparison with default value."""
        return self.value <= other if self.value is not None else True

    def __gt__(self, other):
        """Greater than comparison with default value."""
        return self.value > other if self.value is not None else False

    def __ge__(self, other):
        """Greater than or equal comparison with default value."""
        return self.value >= other if self.value is not None else True

    def __add__(self, other):
        """Add operation with default value."""
        return self.value + other if self.value is not None else other

    def __radd__(self, other):
        """Reverse add operation with default value."""
        return other + self.value if self.value is not None else other

    def __sub__(self, other):
        """Subtract operation with default value."""
        return self.value - other if self.value is not None else -other

    def __rsub__(self, other):
        """Reverse subtract operation with default value."""
        return other - self.value if self.value is not None else other

    def __mul__(self, other):
        """Multiply operation with default value."""
        return self.value * other if self.value is not None else 0

    def __rmul__(self, other):
        """Reverse multiply operation with default value."""
        return other * self.value if self.value is not None else 0

    def __truediv__(self, other):
        """True division operation with default value."""
        return self.value / other if self.value is not None and other != 0 else 0

    def __rtruediv__(self, other):
        """Reverse true division operation with default value."""
        return other / self.value if self.value is not None and self.value != 0 else 0

    def __int__(self) -> int:
        """Convert default value to int."""
        return int(self.value) if self.value is not None else 0

    def __float__(self) -> float:
        """Convert default value to float."""
        return float(self.value) if self.value is not None else 0.0

    def __bool__(self) -> bool:
        """Convert default value to bool."""
        return bool(self.value) if self.value is not None else False


class MockYoutubeDL:
    """Mock yt-dlp."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def download(self, *args, **kwargs):
        return []


# ================================
# MOCK MODULES - Set up sys.modules
# ================================

mock_tk: Any = ModuleType("tkinter")
mock_tk.Tk = MockTkWidget
mock_tk.Frame = MockTkFrame
mock_tk.Label = MockTkLabel
mock_tk.Button = MockTkButton
mock_tk.Entry = MockTkEntry
mock_tk.Listbox = MockTkListbox
mock_tk.messagebox = MockMessagebox()
mock_tk.filedialog = MockFiledialog()

mock_ctk: Any = ModuleType("customtkinter")
mock_ctk.CTk = MockTkWidget2
mock_ctk.CTkFrame = MockTkWidget2
mock_ctk.CTkLabel = MockTkWidget2
mock_ctk.CTkButton = MockTkWidget2
mock_ctk.CTkEntry = MockTkWidget2
mock_ctk.CTkTextbox = MockTkWidget2
mock_ctk.CTkProgressBar = MockTkWidget2
mock_ctk.CTkScrollableFrame = MockTkWidget2
mock_ctk.CTkTabview = MockTkWidget2
mock_ctk.CTkOptionMenu = MockTkWidget2
mock_ctk.CTkSlider = MockTkWidget2
mock_ctk.CTkCheckBox = MockTkWidget2
mock_ctk.CTkSwitch = MockTkWidget2
mock_ctk.CTkRadioButton = MockTkWidget2
mock_ctk.CTkInputDialog = MockTkWidget2
mock_ctk.CTkToplevel = MockTkWidget2
mock_ctk.CTkScrollframe = MockTkWidget2


# Note: We don't mock pydantic anymore - we use the real pydantic in our code
# The MockBaseModel and MockField are kept for backward compatibility
# but pydantic is not mocked in sys.modules since we need the real pydantic

mock_yt_dlp_module: Any = ModuleType("yt_dlp")
mock_yt_dlp_utils: Any = ModuleType("yt_dlp.utils")
mock_yt_dlp_utils.DownloadError = Exception
mock_yt_dlp_module.YoutubeDL = MockYoutubeDL
mock_yt_dlp_module.utils = mock_yt_dlp_utils

# Set up sys.modules to use mocks
sys.modules["tkinter"] = mock_tk
mock_ttk: Any = ModuleType("tkinter.ttk")
mock_ttk.Frame = MockTkFrame
mock_ttk.Label = MockTkLabel
mock_ttk.Button = MockTkButton
mock_ttk.Entry = MockTkEntry
sys.modules["tkinter.ttk"] = mock_ttk
mock_messagebox_module: Any = ModuleType("tkinter.messagebox")
mock_messagebox_module.showerror = lambda title, message: None
mock_messagebox_module.showwarning = lambda title, message: None
mock_messagebox_module.showinfo = lambda title, message: None
sys.modules["tkinter.messagebox"] = mock_messagebox_module

mock_filedialog_module: Any = ModuleType("tkinter.filedialog")
mock_filedialog_module.askopenfilename = lambda **kwargs: ""
mock_filedialog_module.askdirectory = lambda **kwargs: ""
sys.modules["tkinter.filedialog"] = mock_filedialog_module
sys.modules["customtkinter"] = mock_ctk

# Conditionally mock network dependencies so --run-network tests get real code paths.
if not _RUN_NETWORK:
    sys.modules["yt_dlp"] = mock_yt_dlp_module
    sys.modules["yt_dlp.utils"] = mock_yt_dlp_utils
    sys.modules["requests"] = Mock()
    sys.modules["instaloader"] = Mock()

# Always mock PIL (image processing, not needed for unit tests).
sys.modules["PIL"] = Mock()
sys.modules["PIL.Image"] = Mock()
sys.modules["PIL.ImageTk"] = Mock()
sys.modules["PIL.ImageDraw"] = Mock()
sys.modules["PIL.ImageFont"] = Mock()

# ================================
# FIXTURES AND UTILITIES
# ================================


@pytest.fixture(scope="session")
def mock_tkinter():
    """Provide mock tkinter for all tests."""
    return mock_tk


@pytest.fixture(scope="session")
def mock_customtkinter():
    """Provide mock customtkinter for all tests."""
    return mock_ctk


# Removed mock_pydantic fixture - we use real pydantic now


@pytest.fixture(scope="session")
def mock_yt_dlp_fixture():
    """Provide mock yt-dlp for all tests."""
    return mock_yt_dlp_module


# ================================
# PYTEST HOOKS
# ================================


def pytest_addoption(parser) -> None:
    """Register custom CLI options."""
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="run tests that require real network access "
        "(bypasses module-level mocks for requests, yt-dlp, instaloader)",
    )


def pytest_configure(config) -> None:
    """Configure pytest with custom options and markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line(
        "markers",
        "network: marks tests that require real network access "
        "(run with --run-network to execute)",
    )


# ================================
# NETWORK HELPERS
# ================================


def skip_unless_network(
    host: str = "8.8.8.8", port: int = 53, timeout: int = 3
) -> None:
    """Skip the current test if network is unreachable.

    Checks connectivity to a reliable host/port. Skips gracefully so
    CI environments without network don't report failures.
    """
    try:
        socket.create_connection((host, port), timeout=timeout)
    except OSError:
        pytest.skip("network unavailable")


# ================================
# INTEGRATION TEST FIXTURES
# ================================

# Shared mock/stub classes for integration tests that don't need real services.


class MockFileService:
    """Stand-in file service for integration tests.

    Allowed operations succeed without touching the real filesystem
    (except for the temp directory provided by integration_temp_dir).
    """

    def ensure_directory(self, path: str) -> bool:
        return True

    def sanitize_filename(self, filename: str) -> str:
        return filename

    def clean_filename(self, filename: str) -> str:
        return filename

    def download_file(self, url: str, path: str, progress_callback=None):
        _ = (url, path, progress_callback)

        class Result:
            success = True

        return Result()

    def save_text_file(self, content: str, file_path: str) -> bool:
        _ = (content, file_path)
        return True

    def get_unique_filename(
        self, directory: str, base_name: str, extension: str = ""
    ) -> str:
        return f"{directory}/{base_name}{extension}"


class MockErrorNotifier:
    """Stand-in error notifier for integration tests."""

    def handle_service_failure(
        self,
        service: str,
        operation: str,
        error_message: str,
        url: str = "",
        exception: Exception | None = None,
    ) -> None:
        _ = (service, operation, error_message, url, exception)

    def handle_exception(
        self,
        exception: Exception,
        context: str = "",
        service: str = "",
        url: str = "",
    ) -> None:
        _ = (exception, context, service, url)

    def show_error(self, title: str, message: str) -> None:
        _ = (title, message)

    def show_warning(self, title: str, message: str) -> None:
        _ = (title, message)

    def show_info(self, title: str, message: str) -> None:
        _ = (title, message)

    def set_message_queue(self, message_queue) -> None:
        _ = message_queue


@pytest.fixture
def integration_temp_dir():
    """Provide a temporary directory for integration test downloads."""
    td = tempfile.mkdtemp()
    yield td
    shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def integration_config():
    """Provide the real application config for integration tests."""
    from src.core.config import get_config

    return get_config()


@pytest.fixture
def integration_file_service():
    """Provide a MockFileService for integration tests."""
    return MockFileService()


@pytest.fixture
def integration_error_notifier():
    """Provide a MockErrorNotifier for integration tests."""
    return MockErrorNotifier()


@pytest.fixture
def integration_radiojavan_downloader(
    integration_config,
    integration_error_notifier,
    integration_file_service,
):
    """Provide a wired RadioJavanDownloader for integration tests.

    When --run-network is active the downloader uses real network
    dependencies; otherwise module-level mocks are in place.
    """
    from src.services.radiojavan.downloader import RadioJavanDownloader

    return RadioJavanDownloader(
        error_handler=integration_error_notifier,
        file_service=integration_file_service,
        config=integration_config,
    )


@pytest.fixture
def integration_tiktok_downloader(
    integration_config,
    integration_error_notifier,
    integration_file_service,
):
    """Provide a wired TikTokDownloader for integration tests."""
    from src.services.tiktok.downloader import TikTokDownloader

    return TikTokDownloader(
        error_handler=integration_error_notifier,
        file_service=integration_file_service,
        config=integration_config,
    )


# ================================
# UTILITY FUNCTIONS
# ================================


def get_mock_service(service_class, **kwargs):
    """Get a mock instance of a service class."""
    return MagicMock(spec=service_class, **kwargs)


def create_mock_handler(**kwargs):
    """Create a mock handler with default methods."""
    handler = MagicMock()

    # Add default methods that handlers should have
    handler.can_handle = MagicMock(return_value=None)
    handler.get_patterns = MagicMock(return_value=[])
    handler.get_ui_callback = MagicMock(return_value=None)

    # Update with provided kwargs
    for key, value in kwargs.items():
        setattr(handler, key, value)

    return handler


def create_mock_coordinator(**kwargs):
    """Create a mock coordinator with default methods."""
    coordinator = MagicMock()

    # Add default methods that coordinators should have
    coordinator.show_error = MagicMock()
    coordinator.download_manager = MagicMock()
    coordinator.cookie_manager = MagicMock()

    # Update with provided kwargs
    for key, value in kwargs.items():
        setattr(coordinator, key, value)

    return coordinator
