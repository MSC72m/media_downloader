import customtkinter as ctk
import tkinter as tk
from typing import List, Callable, Dict
from src.models import DownloadItem, DownloadStatus


class DownloadListView(ctk.CTkFrame):
    """List view for showing download items and their status."""

    def __init__(self, master, on_selection_change: Callable[[List[int]], None]):
        super().__init__(master)

        self.on_selection_change = on_selection_change
        self._item_line_mapping: Dict[str, int] = {}  # Maps item name to line number

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
        self._item_line_mapping.clear()

        for i, item in enumerate(items):
            status_text = self._format_status(item)
            self.list_view.insert(tk.END, f"{item.name} | {item.url} | {status_text}\n")
            self._item_line_mapping[item.name] = i + 1  # Line numbers are 1-based

    def update_item_progress(self, item: DownloadItem, progress: float):
        """Update progress for a specific item efficiently."""
        line_num = self._item_line_mapping.get(item.name)
        if not line_num:
            return

        # Update the item's progress
        item.progress = progress
        status_text = self._format_status(item)

        # Replace only the status part of the line
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"

        current_line = self.list_view.get(line_start, line_end).strip()
        if current_line:
            # Find the status part (after the second "|")
            parts = current_line.split(" | ")
            if len(parts) >= 3:
                # Update only the status part
                new_line = f"{parts[0]} | {parts[1]} | {status_text}"

                # Store current scroll position
                current_scroll = self.list_view.yview()

                # Replace the line content
                self.list_view.delete(line_start, line_end)
                self.list_view.insert(line_start, new_line)

                # Restore scroll position
                self.list_view.yview_moveto(current_scroll[0])

    @staticmethod
    def _format_status(item: DownloadItem) -> str:
        """Format item status for display."""
        if item.status == DownloadStatus.DOWNLOADING:
            return f"Downloading ({item.progress:.1f}%)"
        elif item.status == DownloadStatus.FAILED:
            return f"Failed: {item.error_message}"
        return item.status.value

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