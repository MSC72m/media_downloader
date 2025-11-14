import tkinter as tk
from collections.abc import Callable
from typing import List

import customtkinter as ctk

from src.core import Download, DownloadStatus


class DownloadListView(ctk.CTkFrame):
    """List view for showing download items and their status."""

    def __init__(self, master, on_selection_change: Callable[[list[int]], None]):
        super().__init__(master)

        self.on_selection_change = on_selection_change
        self._item_line_mapping: dict[str, int] = {}  # Maps item name to line number
        self._downloads: list[Download] = []  # Store actual Download objects

        # Create text widget for displaying downloads
        self.list_view = ctk.CTkTextbox(
            self, activate_scrollbars=True, height=300, font=("Roboto", 12)
        )
        self.list_view.pack(fill=tk.BOTH, expand=True)

        # Bind selection event
        self.list_view.bind("<<Selection>>", self._handle_selection)

        # Enable text selection
        self.list_view.bind("<Control-a>", self._select_all)

    def refresh_items(self, items: list[Download]) -> None:
        """Refresh the displayed items."""
        self.list_view.delete("1.0", tk.END)
        self._item_line_mapping.clear()

        for i, item in enumerate(items):
            status_text = self._format_status(item)
            self.list_view.insert(tk.END, f"{item.name} | {item.url} | {status_text}\n")
            self._item_line_mapping[item.name] = i + 1  # Line numbers are 1-based

    def update_item_progress(self, item: Download, progress: float):
        """Update progress for a specific item efficiently."""
        from src.utils.logger import get_logger

        logger = get_logger(__name__)

        logger.debug(
            f"[DOWNLOAD_LIST] update_item_progress called for {item.name} with progress {progress}"
        )

        line_num = self._item_line_mapping.get(item.name)
        if not line_num:
            logger.warning(f"[DOWNLOAD_LIST] No line mapping found for {item.name}")
            logger.debug(
                f"[DOWNLOAD_LIST] Available mappings: {list(self._item_line_mapping.keys())}"
            )
            return

        logger.debug(f"[DOWNLOAD_LIST] Found line number: {line_num}")

        # Update the item's progress
        item.progress = progress
        status_text = self._format_status(item)
        logger.debug(f"[DOWNLOAD_LIST] Status text: {status_text}")

        # Replace only the status part of the line
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"

        current_line = self.list_view.get(line_start, line_end).strip()
        logger.debug(f"[DOWNLOAD_LIST] Current line: {current_line}")

        if current_line:
            # Find the status part (after the second "|")
            parts = current_line.split(" | ")
            logger.debug(f"[DOWNLOAD_LIST] Line parts: {len(parts)}")

            if len(parts) >= 3:
                # Update only the status part
                new_line = f"{parts[0]} | {parts[1]} | {status_text}"
                logger.debug(f"[DOWNLOAD_LIST] New line: {new_line}")

                # Store current scroll position
                current_scroll = self.list_view.yview()

                # Replace the line content
                self.list_view.delete(line_start, line_end)
                self.list_view.insert(line_start, new_line)

                # Restore scroll position
                if current_scroll and len(current_scroll) > 0:
                    self.list_view.yview_moveto(current_scroll[0])

                logger.debug("[DOWNLOAD_LIST] Progress updated successfully in UI")
            else:
                logger.warning(
                    f"[DOWNLOAD_LIST] Line format unexpected - expected 3+ parts, got {len(parts)}"
                )
        else:
            logger.warning("[DOWNLOAD_LIST] Current line is empty")

    @staticmethod
    def _format_status(item: Download) -> str:
        """Format item status for display."""
        if item.status == DownloadStatus.DOWNLOADING:
            return f"Downloading ({item.progress:.1f}%)"
        elif item.status == DownloadStatus.FAILED:
            return f"Failed: {item.error_message}"
        return item.status.value

    def get_selected_indices(self) -> list[int]:
        """Get indices of selected items."""
        try:
            start = self.list_view.index("sel.first").split(".")[0]
            end = self.list_view.index("sel.last").split(".")[0]
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

    def add_download(self, download: "Download"):
        """Add a new download to the list."""
        # Store the actual Download object
        self._downloads.append(download)

        # Get current content
        current_content = self.list_view.get("1.0", tk.END)

        # Format the new download entry
        status_text = self._format_status(download)
        new_entry = f"{download.name} | {download.url} | {status_text}\n"

        # Add the new download
        self.list_view.insert(tk.END, new_entry)

        # Update the line mapping
        line_num = current_content.count("\n") + 1
        self._item_line_mapping[download.name] = line_num

        # Scroll to the bottom to show the new download
        self.list_view.see(tk.END)

    def has_items(self) -> bool:
        """Check if the download list has any items."""
        return len(self._downloads) > 0

    def get_downloads(self) -> list[Download]:
        """Get all downloads from the list."""
        # Return the stored Download objects instead of parsing text
        return self._downloads.copy()

    def clear_downloads(self) -> None:
        """Clear all downloads from the list."""
        self.list_view.delete("1.0", tk.END)
        self._item_line_mapping.clear()
        self._downloads.clear()

    def remove_downloads(self, indices: List[int]) -> None:
        """Remove downloads by their indices and refresh the list."""
        if not indices:
            return
        # Remove from the stored list (work on a copy, remove highest indices first)
        unique_indices = sorted(
            set(i for i in indices if 0 <= i < len(self._downloads)), reverse=True
        )
        for i in unique_indices:
            del self._downloads[i]
        # Re-render list and rebuild line mapping
        self.refresh_items(self._downloads)

    def remove_completed_downloads(self) -> int:
        """Remove all completed downloads from the list.

        Returns:
            Number of downloads removed
        """
        from src.utils.logger import get_logger

        logger = get_logger(__name__)

        # Find indices of completed downloads
        completed_indices = []
        for i, download in enumerate(self._downloads):
            if download.status == DownloadStatus.COMPLETED:
                completed_indices.append(i)
                logger.debug(
                    f"[DOWNLOAD_LIST] Marking completed download for removal: {download.name}"
                )

        if completed_indices:
            logger.info(
                f"[DOWNLOAD_LIST] Removing {len(completed_indices)} completed downloads"
            )
            self.remove_downloads(completed_indices)
        else:
            logger.debug("[DOWNLOAD_LIST] No completed downloads to remove")

        return len(completed_indices)

    def has_completed_downloads(self) -> bool:
        """Check if there are any completed downloads in the list."""
        return any(
            download.status == DownloadStatus.COMPLETED for download in self._downloads
        )
