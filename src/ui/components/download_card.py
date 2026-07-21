"""Dense queue card optimized for monitoring download work."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

import customtkinter as ctk

from src.core import Download, DownloadStatus
from src.core.enums.theme_event import ThemeEvent
from src.ui.helpers.download_formatting import format_eta, format_file_size, format_speed
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GlassButton, GlassFrame, Palette, resolve_palette

_STATUS_LABELS = {
    DownloadStatus.PENDING: "Queued",
    DownloadStatus.DOWNLOADING: "Downloading",
    DownloadStatus.COMPLETED: "Completed",
    DownloadStatus.FAILED: "Failed",
    DownloadStatus.PAUSED: "Paused",
    DownloadStatus.CANCELLED: "Cancelled",
}

_PLATFORM_LABELS = {
    "youtube": "YT",
    "youtube_music": "YM",
    "spotify": "SP",
    "soundcloud": "SC",
    "tiktok": "TK",
    "instagram": "IG",
    "twitter": "X",
    "pinterest": "PI",
    "radiojavan": "RJ",
}


class DownloadCard(GlassFrame):
    """Compact queue row with title, source, progress, stats, and removal action."""

    def __init__(
        self,
        master,
        download: Download,
        *,
        on_remove: Callable[[Download], None] | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        super().__init__(
            master,
            theme_manager=self._theme_manager,
            elevation="raised",
            interactive=True,
            corner_radius=12,
        )
        self.download = download
        self.on_remove = on_remove
        self.grid_columnconfigure(1, weight=1)
        self._build_ui()
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self._apply_palette(resolve_palette(self._theme_manager))
        self.update_download(download)

    def _build_ui(self) -> None:
        self._source_badge = ctk.CTkLabel(
            self,
            text="DL",
            width=46,
            height=46,
            corner_radius=10,
            font=("Roboto", 11, "bold"),
        )
        self._source_badge.grid(row=0, column=0, rowspan=3, padx=(10, 10), pady=10)

        title_row = ctk.CTkFrame(self, fg_color="transparent")
        title_row.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(9, 0))
        title_row.grid_columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            title_row,
            text="Download",
            font=("Roboto", 13, "bold"),
            anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="ew")

        self._status_label = ctk.CTkLabel(
            title_row,
            text="Queued",
            height=22,
            corner_radius=7,
            font=("Roboto", 10, "bold"),
        )
        self._status_label.grid(row=0, column=1, padx=(8, 7))

        self._remove_button = GlassButton(
            title_row,
            text="Remove",
            width=58,
            height=26,
            variant="ghost",
            command=self._remove,
            theme_manager=self._theme_manager,
        )
        self._remove_button.grid(row=0, column=2, padx=(0, 9))

        self._source_label = ctk.CTkLabel(
            self,
            text="",
            font=("Roboto", 10, "normal"),
            anchor="w",
        )
        self._source_label.grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 4))

        progress_row = ctk.CTkFrame(self, fg_color="transparent")
        progress_row.grid(row=2, column=1, sticky="ew", pady=(0, 9))
        progress_row.grid_columnconfigure(0, weight=1)

        self._progress_bar = ctk.CTkProgressBar(
            progress_row,
            height=5,
            corner_radius=3,
            mode="determinate",
            border_width=0,
        )
        self._progress_bar.grid(row=0, column=0, sticky="ew")

        self._progress_label = ctk.CTkLabel(
            progress_row,
            text="0%",
            width=38,
            font=("Roboto", 10, "bold"),
            anchor="e",
        )
        self._progress_label.grid(row=0, column=1, padx=(8, 0))

        self._meta_label = ctk.CTkLabel(
            self,
            text="",
            width=190,
            font=("Roboto", 10, "normal"),
            anchor="e",
        )
        self._meta_label.grid(row=2, column=2, padx=(12, 10), pady=(0, 9), sticky="e")

    def _service_value(self) -> str:
        service = self.download.service_type
        if service is None:
            return "download"
        value = getattr(service, "value", service)
        return str(value).lower()

    def _status_color(self, palette: Palette) -> str:
        if self.download.status == DownloadStatus.COMPLETED:
            return palette.success
        if self.download.status in {DownloadStatus.FAILED, DownloadStatus.CANCELLED}:
            return palette.error
        if self.download.status == DownloadStatus.PAUSED:
            return palette.warning
        if self.download.status == DownloadStatus.DOWNLOADING:
            return palette.accent
        return palette.text_muted

    def _remove(self) -> None:
        if self.on_remove:
            self.on_remove(self.download)

    def update_download(self, download: Download) -> None:
        self.download = download
        palette = resolve_palette(self._theme_manager)
        service = self._service_value()
        domain = urlparse(download.url).netloc.removeprefix("www.") or service
        title = download.name or domain or "Download"
        if len(title) > 72:
            title = title[:71] + "…"
        self._title_label.configure(text=title)
        self._source_badge.configure(text=_PLATFORM_LABELS.get(service, "DL"))

        detail_parts = [domain]
        if download.quality:
            detail_parts.append(str(download.quality).upper())
        if download.format:
            detail_parts.append(str(download.format).upper())
        self._source_label.configure(text="  ·  ".join(part for part in detail_parts if part))

        value = max(0.0, min(100.0, float(download.progress)))
        self._progress_bar.set(value / 100.0)
        self._progress_label.configure(text=f"{value:.0f}%")
        self._status_label.configure(text=_STATUS_LABELS.get(download.status, "Unknown"))

        stats: list[str] = []
        if download.transferred_bytes is not None and download.total_bytes:
            stats.append(
                f"{format_file_size(download.transferred_bytes)} / {format_file_size(download.total_bytes)}"
            )
        elif download.total_bytes:
            stats.append(format_file_size(download.total_bytes))
        if download.speed and download.speed > 0:
            stats.append(format_speed(download.speed))
        if download.eta_seconds is not None and download.status == DownloadStatus.DOWNLOADING:
            stats.append(f"ETA {format_eta(download.eta_seconds)}")
        self._meta_label.configure(text="  ·  ".join(stats) if stats else "Waiting")
        self._apply_palette(palette)

    def _apply_palette(self, palette: Palette) -> None:
        status_color = self._status_color(palette)
        self._title_label.configure(text_color=palette.text)
        self._source_label.configure(text_color=palette.text_muted)
        self._meta_label.configure(text_color=palette.text_secondary)
        self._progress_label.configure(text_color=palette.text_secondary)
        self._source_badge.configure(
            fg_color=palette.surface_hover,
            text_color=palette.accent,
        )
        self._status_label.configure(
            fg_color=status_color if palette.appearance == "light" else palette.surface_hover,
            text_color="#FFFFFF" if palette.appearance == "light" else status_color,
        )
        self._progress_bar.configure(
            fg_color=palette.progress_track,
            progress_color=status_color
            if self.download.status != DownloadStatus.PENDING
            else palette.accent,
        )

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_palette(resolve_palette(self._theme_manager))

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
