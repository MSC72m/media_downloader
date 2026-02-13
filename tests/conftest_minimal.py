"""Minimal pytest configuration for focused coverage runs."""

import os
import sys
from types import ModuleType
from typing import Any
from unittest.mock import Mock

# Add src to path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

mock_tk: Any = ModuleType("tkinter")
mock_tk.Tk = Mock
mock_tk.Frame = Mock
mock_tk.Label = Mock
mock_tk.Button = Mock
mock_tk.Entry = Mock
sys.modules["tkinter"] = mock_tk

mock_ttk: Any = ModuleType("tkinter.ttk")
mock_ttk.Frame = Mock
mock_ttk.Label = Mock
mock_ttk.Button = Mock
mock_ttk.Entry = Mock
sys.modules["tkinter.ttk"] = mock_ttk

mock_messagebox: Any = ModuleType("tkinter.messagebox")
mock_messagebox.showerror = lambda title, message: None
mock_messagebox.showwarning = lambda title, message: None
mock_messagebox.showinfo = lambda title, message: None
sys.modules["tkinter.messagebox"] = mock_messagebox

mock_filedialog: Any = ModuleType("tkinter.filedialog")
mock_filedialog.askopenfilename = lambda **kwargs: ""
mock_filedialog.askdirectory = lambda **kwargs: ""
sys.modules["tkinter.filedialog"] = mock_filedialog

mock_ctk: Any = ModuleType("customtkinter")
mock_ctk.CTk = Mock
sys.modules["customtkinter"] = mock_ctk

mock_yt_dlp: Any = ModuleType("yt_dlp")
mock_yt_dlp_utils: Any = ModuleType("yt_dlp.utils")
mock_yt_dlp_utils.DownloadError = Exception
mock_yt_dlp.YoutubeDL = Mock
mock_yt_dlp.utils = mock_yt_dlp_utils
sys.modules["yt_dlp"] = mock_yt_dlp
sys.modules["yt_dlp.utils"] = mock_yt_dlp_utils

sys.modules["requests"] = Mock()
sys.modules["instaloader"] = Mock()
sys.modules["pydantic"] = Mock()
