import customtkinter as ctk
import tkinter as tk
from typing import List, Callable
from src.models.download_item import DownloadItem


class DownloadListView(ctk.CTkFrame):
    """List view for showing download items and their status."""

    def __init__(self, master, on_selection_change: Callable[[List[int]], None]):
        super().__init__(master)

        self.on_selection_change = on_selection_change

        # Create text widget for displaying downloads
        self.list_view = ctk.CTkTextbox(
            self,
            activate_scrollbars=True,
            height=300,
            font=("Roboto", 12)
        )
        self.list_view.pack(fill=tk.BOTH, expand=True)

        # Bind selection event
        self.list_view.bind("<<Selection>>", self._handle_selection)

        # Enable text selection
        self.list_view.bind("<Control-a>", self._select_all)

    def refresh_items(self, items: List[DownloadItem]):
        """Refresh the displayed items."""
        self.list_view.delete("1.0", tk.END)
        for item in items:
            status_text = self._format_status(item)
            self.list_view.insert(tk.END, f"{item.name} | {item.url} | {status_text}\n")

    def update_item_progress(self, item: DownloadItem, progress: float):
        """Update progress for a specific item."""
        content = self.list_view.get("1.0", tk.END)
        lines = content.split('\n')

        for i, line in enumerate(lines):
            if line.startswith(f"{item.name} |"):
                status_text = self._format_status(item)
                lines[i] = f"{item.name} | {item.url} | {status_text}"
                break

        self.list_view.delete("1.0", tk.END)
        self.list_view.insert("1.0", '\n'.join(lines))

    @staticmethod
    def _format_status(item: DownloadItem) -> str:
        """Format item status for display."""
        if item.status == "Downloading":
            return f"Downloading ({item.progress:.1f}%)"
        elif item.status == "Failed":
            return f"Failed: {item.error_message}"
        return item.status

    def get_selected_indices(self) -> List[int]:
        """Get indices of selected items."""
        try:
            start = self.list_view.index("sel.first").split('.')[0]
            end = self.list_view.index("sel.last").split('.')[0]
            return list(range(int(start) - 1, int(end)))
        except tk.TclError:  # No selection
            return []

    def _handle_selection(self, event):
        """Handle selection change event."""
        self.on_selection_change(self.get_selected_indices())

    def _select_all(self, event):
        """Handle Ctrl+A selection."""
        self.list_view.tag_add(tk.SEL, "1.0", tk.END)
        self.list_view.mark_set(tk.INSERT, "1.0")
        self.list_view.see(tk.INSERT)
        return "break"  # Prevent default handling