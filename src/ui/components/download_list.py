from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from src.core import Download, DownloadStatus
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DownloadListView(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_selection_change: Callable[[list[int]], None],
        theme_manager: ThemeManager | None = None,
    ):
        super().__init__(master)

        self.on_selection_change = on_selection_change
        self._item_line_mapping: dict[str, int] = {}
        self._downloads: list[Download] = []

        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.list_view = ctk.CTkTextbox(
            self,
            activate_scrollbars=True,
            font=("Roboto", 12),
            corner_radius=8,
            border_width=1,
        )
        self.list_view.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

    def _on_theme_changed(self, appearance, color):
        theme_json = self._theme_manager.get_theme_json()

        frame_config = theme_json.get("CTkFrame", {})
        label_config = theme_json.get("CTkLabel", {})
        if frame_config and label_config:
            self.list_view.configure(
                fg_color=frame_config.get("fg_color"),
                text_color=label_config.get("text_color"),
            )

        self.list_view.bind("<<Selection>>", self._handle_selection)

        self.list_view.bind("<Control-a>", self._select_all)

    def refresh_items(self, items: list[Download]) -> None:
        try:
            self.list_view.delete("1.0", tk.END)
            self._item_line_mapping.clear()

            self._downloads = list(items)

            for i, item in enumerate(items):
                status_text = self._format_status(item)
                self.list_view.insert(tk.END, f"{item.name} | {item.url} | {status_text}\n")
                self._item_line_mapping[item.name] = i + 1

            if self.on_selection_change:
                self.on_selection_change([])
        except Exception as e:
            logger.error(f"[DOWNLOAD_LIST] Error refreshing items: {e}", exc_info=True)

    def update_item_progress(self, item: Download, progress: float):
        try:
            line_num = self._item_line_mapping.get(item.name)
            if not line_num:
                return

            item.progress = progress
            status_text = self._format_status(item)

            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"

            current_line = self.list_view.get(line_start, line_end).strip()
            if not current_line:
                return

            parts = current_line.split(" | ", 2)
            if len(parts) >= 3:
                new_line = f"{parts[0]} | {parts[1]} | {status_text}"

                current_scroll = self.list_view.yview()

                self.list_view.delete(line_start, line_end)
                self.list_view.insert(line_start, new_line)

                if current_scroll and len(current_scroll) > 0:
                    self.list_view.yview_moveto(current_scroll[0])
        except Exception as e:
            logger.error(f"[DOWNLOAD_LIST] Error updating progress: {e}", exc_info=True)

    @staticmethod
    def _format_status(item: Download) -> str:
        if item.status == DownloadStatus.DOWNLOADING:
            return "Downloading"
        if item.status == DownloadStatus.FAILED:
            return f"Failed: {item.error_message}"
        return item.status.value

    def get_selected_indices(self) -> list[int]:
        try:
            start = self.list_view.index("sel.first").split(".")[0]
            end = self.list_view.index("sel.last").split(".")[0]
            return list(range(int(start) - 1, int(end)))
        except tk.TclError:
            return []

    def _handle_selection(self, event):
        self.on_selection_change(self.get_selected_indices())

    def _select_all(self, event):
        self.list_view.tag_add(tk.SEL, "1.0", tk.END)
        self.list_view.mark_set(tk.INSERT, "1.0")
        self.list_view.see(tk.INSERT)
        return "break"

    def add_download(self, download: Download):
        self._downloads.append(download)

        current_content = self.list_view.get("1.0", tk.END)

        status_text = self._format_status(download)
        new_entry = f"{download.name} | {download.url} | {status_text}\n"

        self.list_view.insert(tk.END, new_entry)

        line_num = current_content.count("\n") + 1
        self._item_line_mapping[download.name] = line_num

        self.list_view.see(tk.END)

    def has_items(self) -> bool:
        return len(self._downloads) > 0

    def get_downloads(self) -> list[Download]:
        return self._downloads.copy()

    def clear_downloads(self) -> None:
        self.list_view.delete("1.0", tk.END)
        self._downloads.clear()
        if self.on_selection_change:
            self.on_selection_change([])

    def remove_downloads(self, indices: list[int]) -> None:
        if not indices:
            return
        unique_indices = sorted({i for i in indices if 0 <= i < len(self._downloads)}, reverse=True)
        for i in unique_indices:
            del self._downloads[i]
        self.refresh_items(self._downloads)

    def remove_completed_downloads(self) -> int:
        completed_indices = []
        for i, download in enumerate(self._downloads):
            if download.status == DownloadStatus.COMPLETED:
                completed_indices.append(i)
                logger.debug(
                    f"[DOWNLOAD_LIST] Marking completed download for removal: {download.name}"
                )

        if not completed_indices:
            logger.debug("[DOWNLOAD_LIST] No completed downloads to remove")
            return 0

            logger.info(f"[DOWNLOAD_LIST] Removing {len(completed_indices)} completed downloads")
            self.remove_downloads(completed_indices)
        return len(completed_indices)

    def has_completed_downloads(self) -> bool:
        return any(download.status == DownloadStatus.COMPLETED for download in self._downloads)
