import os
import tkinter as tk
from collections.abc import Callable
from typing import Any

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import resolve_palette


class FileListBox(tk.Listbox):
    """Listbox for displaying files and directories."""

    def __init__(
        self,
        master: Any,
        on_double_click: Callable[[Any], None],
        theme_manager: ThemeManager | None = None,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        palette = resolve_palette(self._theme_manager)

        super().__init__(
            master,
            bg=palette.surface,
            fg=palette.text,
            selectmode=tk.SINGLE,
            selectbackground=palette.accent,
            selectforeground="#FFFFFF",
            highlightbackground=palette.border,
            highlightcolor=palette.border_strong,
            highlightthickness=1,
            borderwidth=0,
            relief="flat",
            activestyle="none",
            font=("Roboto", 12),
        )

        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self.bind("<Double-1>", on_double_click)

    def _on_theme_changed(self, _appearance: str, _color: str) -> None:
        self._apply_theme_colors()

    def _apply_theme_colors(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self.configure(
            bg=palette.surface,
            fg=palette.text,
            selectbackground=palette.accent,
            selectforeground="#FFFFFF",
            highlightbackground=palette.border,
            highlightcolor=palette.border_strong,
        )

    def update_items(self, current_path: str) -> None:
        """Update list with directory contents."""
        self.delete(0, tk.END)

        if current_path != os.path.expanduser("~"):
            self.insert(tk.END, "..")

        try:
            items = os.listdir(current_path)
            directories = []
            files = []

            for item in items:
                full_path = os.path.join(current_path, item)
                if os.path.isdir(full_path):
                    directories.append(item)
                else:
                    files.append(item)

            for directory in sorted(directories):
                self.insert(tk.END, f"📁 {directory}")

            for file in sorted(files):
                self.insert(tk.END, f"📄 {file}")
        except OSError:
            pass

    def get_selected_item(self) -> str | None:
        """Get the currently selected item."""
        selection = self.curselection()
        return self.get(selection[0]) if selection else None

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
