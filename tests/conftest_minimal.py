"""Minimal pytest configuration for 100% coverage testing."""

import sys
import os
from unittest.mock import Mock

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# Mock only what's absolutely necessary for testing
class MockTk:
    def __init__(self, *args, **kwargs):
        pass


class MockCTk:
    def __init__(self, *args, **kwargs):
        pass


# Mock tkinter imports to avoid GUI dependencies
sys.modules["tkinter"] = MockTk
sys.modules["tkinter.ttk"] = MockTk
sys.modules["tkinter.messagebox"] = MockTk
sys.modules["tkinter.filedialog"] = MockTk
sys.modules["customtkinter"] = MockCTk


# Mock messagebox functions
class MockMessagebox:
    def showerror(self, title, message):
        pass

    def showwarning(self, title, message):
        pass

    def showinfo(self, title, message):
        pass


sys.modules["tkinter.messagebox"] = MockMessagebox()


# Mock yt_dlp to avoid external dependencies
class MockYoutubeDL:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def download(self, *args, **kwargs):
        return []


class MockDownloadError(Exception):
    pass


mock_yt_dlp = type(
    "MockModule",
    (),
    {
        "YoutubeDL": MockYoutubeDL,
        "utils": type("MockModule", (), {"DownloadError": MockDownloadError})(),
    },
)()

sys.modules["yt_dlp"] = mock_yt_dlp
sys.modules["yt_dlp.utils"] = mock_yt_dlp.utils

# Mock other external dependencies
sys.modules["requests"] = Mock()
sys.modules["instaloader"] = Mock()
sys.modules["pydantic"] = Mock()
