"""Queue-first scrollable download list with one integrated empty state."""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Sequence

import customtkinter as ctk

from src.core import Download, DownloadStatus
from src.core.enums.theme_event import ThemeEvent
from src.ui.components.download_card import DownloadCard
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GlassFrame, resolve_both_palettes, resolve_palette


class DownloadCardList(GlassFrame):
    """Canonical queue view preserving the coordinator's list protocol."""

    def __init__(
        self,
        master,
        *,
        on_remove: Callable[[Download], None] | None = None,
        on_summary: Callable[[Sequence[Download]], None] | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        super().__init__(
            master, theme_manager=self._theme_manager, elevation="base", corner_radius=14
        )
        self.on_remove = on_remove
        self.on_summary = on_summary
        self._downloads: list[Download] = []
        self._cards: list[DownloadCard] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(11, 7))
        header.grid_columnconfigure(0, weight=1)

        self._heading_label = ctk.CTkLabel(
            header,
            text="Download queue",
            font=("Roboto", 14, "bold"),
            anchor="w",
        )
        self._heading_label.grid(row=0, column=0, sticky="w")
        self._count_label = ctk.CTkLabel(
            header,
            text="0 items",
            font=("Roboto", 10, "normal"),
            anchor="e",
        )
        self._count_label.grid(row=0, column=1, sticky="e")

        self._scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
        )
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=7, pady=(0, 7))
        self._scroll.grid_columnconfigure(0, weight=1)

        self._empty = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._empty.grid(row=0, column=0, sticky="nsew", padx=20, pady=70)
        self._empty.grid_columnconfigure(0, weight=1)
        self._empty_title = ctk.CTkLabel(
            self._empty,
            text="Queue is empty",
            font=("Roboto", 14, "bold"),
        )
        self._empty_title.grid(row=0, column=0)
        self._empty_hint = ctk.CTkLabel(
            self._empty,
            text="Paste a link above to add your first download.",
            font=("Roboto", 11, "normal"),
        )
        self._empty_hint.grid(row=1, column=0, pady=(4, 0))

        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self._apply_palette()

    def refresh_items(self, downloads: list[Download]) -> None:
        self._downloads = list(downloads)
        self._rebuild()
        self._notify_state()

    def sync_from(self, downloads: list[Download]) -> None:
        if len(downloads) != len(self._cards) or any(
            current is not incoming
            for current, incoming in zip(self._downloads, downloads, strict=False)
        ):
            self.refresh_items(downloads)
            return
        self._downloads = list(downloads)
        for card, download in zip(self._cards, downloads, strict=False):
            card.update_download(download)
        self._notify_state()

    def update_item_progress(self, item: Download, progress: float) -> None:
        item.progress = progress
        for index, current in enumerate(self._downloads):
            if current is item or (current.url == item.url and current.name == item.name):
                self._downloads[index] = item
                self._cards[index].update_download(item)
                self._notify_state()
                return

    def add_download(self, download: Download) -> None:
        self.refresh_items([*self._downloads, download])
        with contextlib.suppress(Exception):
            self._scroll._parent_canvas.yview_moveto(1.0)  # pyright: ignore[reportAttributeAccessIssue]

    def remove_downloads(self, indices: list[int]) -> None:
        remove = {index for index in indices if 0 <= index < len(self._downloads)}
        self.refresh_items(
            [download for index, download in enumerate(self._downloads) if index not in remove]
        )

    def clear_downloads(self) -> None:
        self.refresh_items([])

    def get_downloads(self) -> list[Download]:
        return self._downloads.copy()

    def has_items(self) -> bool:
        return bool(self._downloads)

    def has_completed_downloads(self) -> bool:
        return any(download.status == DownloadStatus.COMPLETED for download in self._downloads)

    def remove_completed_downloads(self) -> int:
        completed = [
            index
            for index, download in enumerate(self._downloads)
            if download.status == DownloadStatus.COMPLETED
        ]
        self.remove_downloads(completed)
        return len(completed)

    def _rebuild(self) -> None:
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        for index, download in enumerate(self._downloads):
            card = DownloadCard(
                self._scroll,
                download,
                on_remove=self.on_remove,
                theme_manager=self._theme_manager,
            )
            card.grid(row=index, column=0, sticky="ew", padx=2, pady=(0, 7))
            self._cards.append(card)

    def _notify_state(self) -> None:
        count = len(self._downloads)
        self._count_label.configure(text=f"{count} item" if count == 1 else f"{count} items")
        if count:
            self._empty.grid_remove()
        else:
            self._empty.grid()
        if self.on_summary:
            self.on_summary(self._downloads)

    def _apply_palette(self) -> None:
        palette = resolve_palette(self._theme_manager)
        light_palette, dark_palette = resolve_both_palettes(self._theme_manager)
        self._heading_label.configure(text_color=palette.text)
        self._count_label.configure(text_color=palette.text_muted)
        self._empty_title.configure(text_color=palette.text_secondary)
        self._empty_hint.configure(text_color=palette.text_muted)
        with contextlib.suppress(Exception):
            self._scroll.configure(
                fg_color=[light_palette.surface, dark_palette.surface],
                scrollbar_button_color=[
                    light_palette.border_strong,
                    dark_palette.border_strong,
                ],
                scrollbar_button_hover_color=[
                    light_palette.text_muted,
                    dark_palette.text_muted,
                ],
            )

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_palette()

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        for card in self._cards:
            with contextlib.suppress(Exception):
                card.destroy()
        self._cards.clear()
        super().destroy()
