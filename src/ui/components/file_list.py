import os
import tkinter as tk
from collections.abc import Callable

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager


class FileListBox(tk.Listbox):
    """Listbox for displaying files and directories."""

    def __init__(
        self,
        master,
        on_double_click: Callable,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager()
        colors = self._theme_manager.get_colors()

        super().__init__(
            master,
            bg=colors.get("surface", "#2a2d2e"),
            fg=colors.get("text_on_surface", "white"),
            selectmode=tk.SINGLE,
            selectbackground=colors.get("select_bg", "#1f538d"),
            font=("Roboto", 12),
        )

        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self.bind("<Double-1>", on_double_click)

    def _on_theme_changed(self, appearance, color) -> None:
        self._apply_theme_colors()

    def _apply_theme_colors(self) -> None:
        colors = self._theme_manager.get_colors()
        self.configure(
            bg=colors.get("surface", "#2a2d2e"),
            fg=colors.get("text_on_surface", "white"),
            selectbackground=colors.get("select_bg", "#1f538d"),
        )

    def update_items(self, current_path: str) -> None:
        """Update list with directory contents."""
        self.delete(0, tk.END)

        # Add parent directory option
        if current_path != os.path.expanduser("~"):
            self.insert(tk.END, "..")

        try:
            # List directories first
            items = os.listdir(current_path)
            directories = []
            files = []

            for item in items:
                full_path = os.path.join(current_path, item)
                if os.path.isdir(full_path):
                    directories.append(item)
                else:
                    files.append(item)

            # Insert sorted directories and files
            for directory in sorted(directories):
                self.insert(tk.END, f"📁 {directory}")

            for file in sorted(files):
                self.insert(tk.END, f"📄 {file}")

        except OSError:
            # Handle directory access errors
            pass

    def get_selected_item(self) -> str | None:
        """Get the currently selected item."""
        selection = self.curselection()
        return self.get(selection[0]) if selection else None

    def destroy(self) -> None:
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
