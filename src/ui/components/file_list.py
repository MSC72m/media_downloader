import os
import tkinter as tk
from typing import Callable, Optional


class FileListBox(tk.Listbox):
    """Listbox for displaying files and directories."""

    def __init__(self, master, on_double_click: Callable):
        super().__init__(
            master,
            bg="#2a2d2e",
            fg="white",
            selectmode=tk.SINGLE,
            selectbackground="#1f538d",
            font=("Roboto", 12)
        )

        self.bind('<Double-1>', on_double_click)

    def update_items(self, current_path: str):
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

        except OSError as e:
            # Handle directory access errors
            pass

    def get_selected_item(self) -> Optional[str]:
        """Get the currently selected item."""
        selection = self.curselection()
        return self.get(selection[0]) if selection else None