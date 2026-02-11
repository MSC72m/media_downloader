import re
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager

from ..dialogs.input_dialog import CenteredInputDialog

_YOUTUBE_DOMAIN_PATTERN = re.compile(r"(?:youtube\.com|youtu\.be)", re.IGNORECASE)


class URLEntryFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_add: Callable[[str, str], None],  # Callback signature: (url: str, name: str) -> None
        on_youtube_detected: Callable[[str], None] | None = None,
        theme_manager: ThemeManager | None = None,
    ):
        super().__init__(master, fg_color="transparent")

        self.on_add = on_add
        self.on_youtube_detected = on_youtube_detected

        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.grid_columnconfigure(0, weight=1)

        input_height = 45

        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="Enter a URL",
            height=input_height,
            font=("Roboto", 13),
            corner_radius=8,
            border_width=1,
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _e: self.handle_add())

        self.add_button = ctk.CTkButton(
            self,
            text="Add",
            command=self.handle_add,
            width=95,
            height=input_height,
            font=("Roboto", 13),
            corner_radius=8,
            border_width=0,
        )
        self.add_button.grid(row=0, column=1, sticky="ns")

        self._apply_theme_colors()

    @staticmethod
    def _normalize_color(color):
        """Extract a single color string from a theme color value (may be list/tuple)."""
        if isinstance(color, list | tuple) and len(color) > 0:
            return color[0] if isinstance(color[0], str) else str(color[0])
        if not isinstance(color, str):
            return str(color)
        return color

    def _apply_theme_colors(self):
        theme_json = self._theme_manager.get_theme_json()

        entry_config = theme_json.get("CTkEntry", {})
        if entry_config:
            fg_color = self._normalize_color(entry_config.get("fg_color"))
            border_color = self._normalize_color(entry_config.get("border_color"))
            text_color = self._normalize_color(entry_config.get("text_color"))

            self.url_entry.configure(
                fg_color=fg_color,
                border_color=border_color,
                text_color=text_color,
            )

        button_config = theme_json.get("CTkButton", {})
        if button_config:
            button_color = self._normalize_color(button_config.get("fg_color"))
            hover_color = self._normalize_color(button_config.get("hover_color"))
            text_color = self._normalize_color(button_config.get("text_color"))

            self.add_button.configure(
                fg_color=button_color,
                hover_color=hover_color,
                text_color=text_color,
            )

    def _on_theme_changed(self, appearance, color):
        self._apply_theme_colors()

    def handle_add(self):
        url = self.url_entry.get().strip()
        if not url:
            return

        if self.on_youtube_detected and _YOUTUBE_DOMAIN_PATTERN.search(url):
            self.on_youtube_detected(url)
            self.clear()
            return

        dialog = CenteredInputDialog(text="Enter a name for this link:", title="Link Name")
        name = dialog.get_input()

        if name:
            self.on_add(url, name)
            self.clear()

    def clear(self):
        self.url_entry.delete(0, tk.END)
