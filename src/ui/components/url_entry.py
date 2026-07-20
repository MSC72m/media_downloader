from __future__ import annotations

import contextlib
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
    ) -> None:
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
        self._install_clipboard_support()

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

    def _install_clipboard_support(self) -> None:
        """Make paste work regardless of keyboard layout (issue #14).

        Tk's default Ctrl+V binds the Latin ``v`` keysym, which never fires on
        non-Latin layouts (Persian, Russian, ...), so users literally cannot
        paste. Add a right-click context menu (layout-independent) plus explicit
        paste/copy/cut bindings for the common accelerators.
        """
        entry = self.url_entry
        for seq in ("<Control-v>", "<Control-V>", "<Command-v>"):
            entry.bind(seq, self._paste)
        for seq in ("<Control-c>", "<Control-C>", "<Command-c>"):
            entry.bind(seq, self._copy)
        for seq in ("<Control-x>", "<Control-X>", "<Command-x>"):
            entry.bind(seq, self._cut)

        self._context_menu = tk.Menu(entry, tearoff=0)
        self._context_menu.add_command(label="Paste", command=self._paste)
        self._context_menu.add_command(label="Copy", command=self._copy)
        self._context_menu.add_command(label="Cut", command=self._cut)
        # Button-3 = right click (Win/Linux); Button-2 = right click (macOS).
        for seq in ("<Button-3>", "<Button-2>"):
            entry.bind(seq, self._show_context_menu)

    def _show_context_menu(self, event: tk.Event) -> str:
        with contextlib.suppress(Exception):
            self._context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _paste(self, _event: tk.Event | None = None) -> str:
        try:
            text = self.url_entry.clipboard_get()
        except tk.TclError:
            return "break"
        with contextlib.suppress(tk.TclError):
            if self.url_entry.selection_present():
                self.url_entry.delete("sel.first", "sel.last")
        self.url_entry.insert(tk.INSERT, text.strip())
        return "break"

    def _copy(self, _event: tk.Event | None = None) -> str:
        with contextlib.suppress(tk.TclError):
            if self.url_entry.selection_present():
                self.clipboard_clear()
                self.clipboard_append(self.url_entry.selection_get())
        return "break"

    def _cut(self, _event: tk.Event | None = None) -> str:
        self._copy()
        with contextlib.suppress(tk.TclError):
            if self.url_entry.selection_present():
                self.url_entry.delete("sel.first", "sel.last")
        return "break"

    @staticmethod
    def _normalize_color(color):
        if isinstance(color, list | tuple) and len(color) > 0:
            return color[0] if isinstance(color[0], str) else str(color[0])
        if not isinstance(color, str):
            return str(color)
        return color

    def _apply_theme_colors(self) -> None:
        theme_json = self._theme_manager.get_theme_json()

        if entry_config := theme_json.get("CTkEntry", {}):
            fg_color = self._normalize_color(entry_config.get("fg_color"))
            border_color = self._normalize_color(entry_config.get("border_color"))
            text_color = self._normalize_color(entry_config.get("text_color"))

            self.url_entry.configure(
                fg_color=fg_color,
                border_color=border_color,
                text_color=text_color,
            )

        if button_config := theme_json.get("CTkButton", {}):
            button_color = self._normalize_color(button_config.get("fg_color"))
            hover_color = self._normalize_color(button_config.get("hover_color"))
            text_color = self._normalize_color(button_config.get("text_color"))

            self.add_button.configure(
                fg_color=button_color,
                hover_color=hover_color,
                text_color=text_color,
            )

    def _on_theme_changed(self, appearance, color) -> None:
        self._apply_theme_colors()

    def handle_add(self) -> None:
        if not (url := self.url_entry.get().strip()):
            return

        if self.on_youtube_detected and _YOUTUBE_DOMAIN_PATTERN.search(url):
            self.on_youtube_detected(url)
            self.clear()
            return

        dialog = CenteredInputDialog(text="Enter a name for this link:", title="Link Name")
        if name := dialog.get_input():
            self.on_add(url, name)
            self.clear()

    def clear(self) -> None:
        self.url_entry.delete(0, tk.END)

    def destroy(self) -> None:
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
