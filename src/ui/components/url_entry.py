import tkinter as tk
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager
from ..dialogs.input_dialog import CenteredInputDialog


class URLEntryFrame(ctk.CTkFrame):
    """Frame for URL input and add button."""

    def __init__(
        self,
        master,
        on_add: Callable[
            [str, str], None
        ],  # Callback signature: (url: str, name: str) -> None
        on_youtube_detected: Callable[[str], None] | None = None,
        theme_manager: Optional[ThemeManager] = None,
    ):
        super().__init__(master, fg_color="transparent")

        self.on_add = on_add
        self.on_youtube_detected = on_youtube_detected

        # Subscribe to theme manager
        root_window = master.winfo_toplevel()
        self._theme_manager = theme_manager or ThemeManager.get_instance(root_window)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # URL Entry with modern styling
        self.url_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Enter a URL", 
            height=42, 
            font=("Roboto", 14),
            corner_radius=12,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda e: self.handle_add())

        # Add Button with modern styling
        self.add_button = ctk.CTkButton(
            self,
            text="Add",
            command=self.handle_add,
            width=110,
            height=42,
            font=("Roboto", 14),
            corner_radius=12,
        )
        self.add_button.grid(row=0, column=1)
    
    def _on_theme_changed(self, appearance, color):
        """Handle theme change event."""
        # Entry and button will automatically update with CTK theme change
        pass

    def handle_add(self):
        """Handle add button click."""
        url = self.url_entry.get().strip()
        if url:
            # Check if it's a YouTube URL and open in new window
            if self.on_youtube_detected and ("youtube.com" in url or "youtu.be" in url):
                self.on_youtube_detected(url)
                self.clear()  # Clear URL after YouTube detection
                return  # Don't continue with normal flow for YouTube URLs

            dialog = CenteredInputDialog(
                text="Enter a name for this link:", title="Link Name"
            )
            name = dialog.get_input()

            if name:
                self.on_add(url, name)  # Call with two arguments
                self.clear()

    def clear(self):
        """Clear the URL entry field."""
        self.url_entry.delete(0, tk.END)
