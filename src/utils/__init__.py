"""Utilities for the media downloader application.

Note: Do NOT import tkinter-dependent modules here to avoid hard runtime deps
at package import time. Import GUI utilities (window) where needed.
"""

from .logger import get_logger

__all__ = ["get_logger"]
