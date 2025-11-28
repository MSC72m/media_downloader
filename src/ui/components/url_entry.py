import re
import tkinter as tk
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import get_theme_manager, ThemeManager
from ..dialogs.input_dialog import CenteredInputDialog

# Compiled regex patterns for efficient URL matching
_YOUTUBE_DOMAIN_PATTERN = re.compile(r"(?:youtube\.com|youtu\.be)", re.IGNORECASE)


class URLEntryFrame(ctk.CTkFrame):
    """Frame for URL input and add button."""

    def __init__(
        self,
        master,
        on_add: Callable[
            [str, str], None
        ],  # Callback signature: (url: str, name: str) -> None
        on_youtube_detected: Callable[[str], None] | None = None,
        theme_manager: Optional["ThemeManager"] = None,
    ):
        super().__init__(master, fg_color="transparent")

        self.on_add = on_add
        self.on_youtube_detected = on_youtube_detected

        # Subscribe to theme manager - injected with default
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # URL Entry with modern styling - sleek design
        self.url_entry = ctk.CTkEntry(
            self, 
            placeholder_text="Enter a URL", 
            height=46, 
            font=("Roboto", 13),
            corner_radius=12,
            border_width=1,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.url_entry.bind("<Return>", lambda e: self.handle_add())

        # Add Button with modern styling - primary action with emphasis
        self.add_button = ctk.CTkButton(
            self,
            text="Add",
            command=self.handle_add,
            width=110,
            height=46,
            font=("Roboto", 14, "bold"),
            corner_radius=12,
            border_width=0,
        )
        self.add_button.grid(row=0, column=1)
    
    def _on_theme_changed(self, appearance, color):
        """Handle theme change event - apply custom colors."""
        colors = self._theme_manager.get_colors()
        theme_json = self._theme_manager.get_theme_json()
        
        # Apply custom colors to entry
        entry_config = theme_json.get("CTkEntry", {})
        if entry_config:
            self.url_entry.configure(
                fg_color=entry_config.get("fg_color"),
                border_color=entry_config.get("border_color"),
                text_color=entry_config.get("text_color"),
            )
        
        # Apply custom colors to add button
        button_config = theme_json.get("CTkButton", {})
        if button_config:
            self.add_button.configure(
                fg_color=button_config.get("fg_color"),
                hover_color=button_config.get("hover_color"),
                text_color=button_config.get("text_color"),
            )

    def handle_add(self):
        """Handle add button click."""
        url = self.url_entry.get().strip()
        if not url:
            return
        
        # Check if it's a YouTube URL using regex pattern
        if self.on_youtube_detected and _YOUTUBE_DOMAIN_PATTERN.search(url):
            self.on_youtube_detected(url)
            self.clear()
            return

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
