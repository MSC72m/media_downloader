"""Unified compact footer implementing action and status UI protocols."""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable, Sequence

import customtkinter as ctk

from src.core import Download, DownloadStatus
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GlassButton, GlassFrame, GradientButton, resolve_palette


class AppFooter(GlassFrame):
    """Queue summary, actions, transient status, and overall progress in one region."""

    def __init__(
        self,
        master,
        *,
        on_clear: Callable[[], None],
        on_download: Callable[[], None],
        on_manage_files: Callable[[], None],
        theme_manager: ThemeManager | None = None,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        super().__init__(
            master, theme_manager=self._theme_manager, elevation="base", corner_radius=13
        )
        self._coordinator_enabled = True
        self._has_items = False
        self._message_after_id: str | None = None

        self.grid_columnconfigure(1, weight=1)

        summary = ctk.CTkFrame(self, fg_color="transparent")
        summary.grid(row=0, column=0, padx=(12, 8), pady=(8, 6), sticky="w")
        self._summary_label = ctk.CTkLabel(
            summary,
            text="Queue 0  ·  Finished 0  ·  Failed 0",
            font=("Roboto", 11, "normal"),
            anchor="w",
        )
        self._summary_label.pack(anchor="w")
        self._status_label = ctk.CTkLabel(
            summary,
            text="Ready",
            font=("Roboto", 10, "normal"),
            anchor="w",
        )
        self._status_label.pack(anchor="w", pady=(1, 0))

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=0, column=2, padx=8, pady=7, sticky="e")

        self.manage_button = GlassButton(
            actions,
            text="Open folder",
            width=88,
            height=34,
            variant="ghost",
            command=on_manage_files,
            theme_manager=self._theme_manager,
        )
        self.manage_button.grid(row=0, column=0, padx=(0, 4))
        # Compatibility for helpers that inspect ``app.status_bar.status_label``.
        self.status_label = self._status_label

        self.clear_button = GlassButton(
            actions,
            text="Clear",
            width=58,
            height=34,
            variant="secondary",
            command=on_clear,
            theme_manager=self._theme_manager,
        )
        self.clear_button.grid(row=0, column=1, padx=4)

        self.download_button = GradientButton(
            actions,
            text="Download all",
            command=on_download,
            width=116,
            height=34,
            corner_radius=9,
            theme_manager=self._theme_manager,
        )
        self.download_button.grid(row=0, column=2, padx=(4, 0))

        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=2,
            corner_radius=1,
            border_width=0,
        )
        self.progress_bar.grid(row=1, column=0, columnspan=3, sticky="ew", padx=1, pady=(0, 1))
        self.progress_bar.set(0)

        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self._apply_palette()
        self._sync_button_states()

    def update_queue(self, downloads: Sequence[Download]) -> None:
        active_statuses = {
            DownloadStatus.PENDING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.PAUSED,
        }
        active = sum(item.status in active_statuses for item in downloads)
        finished = sum(item.status == DownloadStatus.COMPLETED for item in downloads)
        failed = sum(
            item.status in {DownloadStatus.FAILED, DownloadStatus.CANCELLED} for item in downloads
        )
        self._has_items = bool(downloads)
        self._summary_label.configure(
            text=f"Queue {active}  ·  Finished {finished}  ·  Failed {failed}"
        )
        self._sync_button_states()

    def update_queue_counts(self, active: int, finished: int, failed: int) -> None:
        self._has_items = (active + finished + failed) > 0
        self._summary_label.configure(
            text=f"Queue {active}  ·  Finished {finished}  ·  Failed {failed}"
        )
        self._sync_button_states()

    def _sync_button_states(self) -> None:
        can_process = self._coordinator_enabled and self._has_items
        self.download_button.configure(state="normal" if can_process else "disabled")
        self.clear_button.configure(state="normal" if can_process else "disabled")
        self.manage_button.configure(state="normal")

    def set_enabled(self, enabled: bool) -> None:
        self._coordinator_enabled = enabled
        self._sync_button_states()

    def set_button_state(self, button_name: str, state: str) -> None:
        button = {
            "download": self.download_button,
            "clear": self.clear_button,
            "manage": self.manage_button,
        }.get(button_name)
        if button is not None:
            button.configure(state=state)

    def update_button_states(self, has_selection: bool, has_items: bool) -> None:
        self._has_items = has_items
        self._sync_button_states()

    def _set_message(self, message: str, role: str = "normal") -> None:
        if self._message_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._message_after_id)
        palette = resolve_palette(self._theme_manager)
        color = {
            "error": palette.error,
            "warning": palette.warning,
            "success": palette.success,
        }.get(role, palette.text_secondary)
        self._status_label.configure(text=message, text_color=color)
        self._message_after_id = self.after(7000, self._reset_message)

    def _reset_message(self) -> None:
        self._message_after_id = None
        palette = resolve_palette(self._theme_manager)
        self._status_label.configure(text="Ready", text_color=palette.text_muted)

    def show_message(self, message: str) -> None:
        role = "success" if "complet" in message.lower() or "ready" in message.lower() else "normal"
        self._set_message(message, role)

    def show_error(self, message: str) -> None:
        self._set_message(f"Error · {message}", "error")

    def show_warning(self, message: str) -> None:
        self._set_message(f"Warning · {message}", "warning")

    def update_progress(self, progress: float) -> None:
        value = max(0.0, min(100.0, progress))
        self.progress_bar.set(value / 100.0)
        if 0 < value < 100:
            self._status_label.configure(text=f"Downloading · {value:.0f}%")
        elif value >= 100:
            self._set_message("Downloads completed", "success")

    def reset(self) -> None:
        self.progress_bar.set(0)
        self._reset_message()

    def _apply_palette(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self._summary_label.configure(text_color=palette.text)
        self._status_label.configure(text_color=palette.text_muted)
        self.progress_bar.configure(
            fg_color=palette.progress_track,
            progress_color=palette.accent,
        )

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_palette()

    def destroy(self) -> None:
        if self._message_after_id is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._message_after_id)
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
