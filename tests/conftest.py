"""Pytest configuration and mocking for testing without GUI dependencies."""

import sys
import os
import pytest
from unittest.mock import Mock, MagicMock

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ================================
# MOCK CLASSES - Define early before use
# ================================

class MockTk:
    """Mock tkinter base class."""
    def __init__(self, *args, **kwargs):
        pass

class MockTkWidget:
    """Mock tkinter widget base class."""
    def __init__(self, *args, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def grid(self, **kwargs):
        pass

    def place(self, **kwargs):
        pass

    def configure(self, **kwargs):
        pass

    def cget(self, *args):
        return None

    def bind(self, *args, **kwargs):
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
    def __init__(self, *args, **kwargs):
        pass

class MockTkWidget2:
    """Mock customtkinter widget base class."""
    def __init__(self, *args, **kwargs):
        pass

    def pack(self, **kwargs):
        pass

    def grid(self, **kwargs):
        pass

    def place(self, **kwargs):
        pass

    def configure(self, **kwargs):
        pass

    def cget(self, *args):
        return None

    def bind(self, *args, **kwargs):
        return None

class MockMessagebox:
    """Mock messagebox functions."""
    def showerror(self, title, message):
        pass

    def showwarning(self, title, message):
        pass

    def showinfo(self, title, message):
        pass

class MockFiledialog:
    """Mock file dialog functions."""
    def askopenfilename(self, **kwargs):
        return ""

    def askdirectory(self, **kwargs):
        return ""

class MockBaseModel:
    """Mock Pydantic BaseModel."""
    def __init__(self, **kwargs):
        # Get default values from class attributes that are MockField objects
        for key, value in self.__class__.__dict__.items():
            if not key.startswith('_') and hasattr(value, 'value'):
                # This is a MockField with a default value
                if key not in kwargs:
                    setattr(self, key, value.value)

        # Set provided kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockField:
    """Mock Pydantic Field."""
    def __init__(self, default=None, default_factory=None, description=None, **kwargs):
        # Store the actual value that should be returned when the field is accessed
        if default_factory is not None:
            self.value = default_factory() if callable(default_factory) else default_factory
        else:
            self.value = default
        self.default = default
        self.default_factory = default_factory
        self.description = description

    def __str__(self):
        """Return the default value as string representation."""
        return str(self.value) if self.value is not None else ""

    def __repr__(self):
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

    def __int__(self):
        """Convert default value to int."""
        return int(self.value) if self.value is not None else 0

    def __float__(self):
        """Convert default value to float."""
        return float(self.value) if self.value is not None else 0.0

    def __bool__(self):
        """Convert default value to bool."""
        return bool(self.value) if self.value is not None else False

class MockYoutubeDL:
    """Mock yt-dlp."""
    def __init__(self, *args, **kwargs):
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

# Create mock modules
mock_tk = MockTk()
mock_tk.Tk = MockTkWidget
mock_tk.Frame = MockTkFrame
mock_tk.Label = MockTkLabel
mock_tk.Button = MockTkButton
mock_tk.Entry = MockTkEntry
mock_tk.Listbox = MockTkListbox
mock_tk.messagebox = MockMessagebox()
mock_tk.filedialog = MockFiledialog()

mock_ctk = MockCTk()
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

mock_pydantic = type('MockModule', (), {
    'BaseModel': MockBaseModel,
    'Field': MockField
})()

mock_yt_dlp = type('MockModule', (), {
    'YoutubeDL': MockYoutubeDL,
    'utils': type('MockModule', (), {
        'DownloadError': Exception
    })()
})()

# Set up sys.modules to use mocks
sys.modules['tkinter'] = mock_tk
sys.modules['tkinter.ttk'] = MockTk
sys.modules['tkinter.messagebox'] = MockMessagebox()
sys.modules['tkinter.filedialog'] = MockFiledialog()
sys.modules['customtkinter'] = mock_ctk
sys.modules['yt_dlp'] = mock_yt_dlp
sys.modules['yt_dlp.utils'] = mock_yt_dlp.utils
sys.modules['pydantic'] = mock_pydantic

# Mock other external dependencies
sys.modules['requests'] = Mock()
sys.modules['instaloader'] = Mock()
sys.modules['PIL'] = Mock()
sys.modules['PIL.Image'] = Mock()
sys.modules['PIL.ImageTk'] = Mock()
sys.modules['PIL.ImageDraw'] = Mock()
sys.modules['PIL.ImageFont'] = Mock()

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

@pytest.fixture(scope="session")
def mock_pydantic():
    """Provide mock pydantic for all tests."""
    return mock_pydantic

@pytest.fixture(scope="session")
def mock_yt_dlp():
    """Provide mock yt-dlp for all tests."""
    return mock_yt_dlp

# ================================
# PYTEST CONFIGURATION
# ================================

def pytest_configure(config):
    """Configure pytest with custom options."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
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