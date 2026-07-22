"""Shared gradient-backed lifecycle for every application dialog."""

from __future__ import annotations

import contextlib
import queue
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GradientBackdrop, resolve_palette
from src.utils.window import WindowCenterMixin


class BaseDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Canonical top-level window with one gradient and one theme lifecycle.

    Dialog-specific content belongs under :attr:`content_parent`. Visible cards
    should use the shared glass surfaces from ``src.ui.visual_system``.
    """

    def __init__(
        self,
        parent: Any,
        *,
        title: str = "Download",
        config: AppConfig | None = None,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)

        self._cfg = config or get_config()
        root = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        self._theme_manager = theme_manager or get_theme_manager(root)
        self._dialog_destroyed = False
        self._theme_refresh_callbacks: list[Callable[[], None]] = []
        self._ui_callbacks: queue.SimpleQueue[Callable[[], None]] = queue.SimpleQueue()
        self._ui_queue_after_id: str | None = None
        self._previous_grab: Any | None = None

        self.title(title)
        self.transient(parent)
        self.resizable(True, True)
        self.withdraw()

        palette = resolve_palette(self._theme_manager)
        self.configure(fg_color=palette.background_mid)
        self.background = GradientBackdrop(self, theme_manager=self._theme_manager)
        self.background.place(x=0, y=0, relwidth=1, relheight=1)
        self.content_parent = self.background

        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._handle_dialog_theme_changed)
        self._ui_queue_after_id = self.after(25, self._drain_ui_callbacks)

    def call_on_ui_thread(self, callback: Callable[[], None]) -> None:
        """Queue work from any thread for execution by this dialog's Tk loop."""
        if not self._dialog_destroyed:
            self._ui_callbacks.put(callback)

    def _drain_ui_callbacks(self) -> None:
        self._ui_queue_after_id = None
        if self._dialog_destroyed:
            return
        while not self._ui_callbacks.empty():
            callback = self._ui_callbacks.get_nowait()
            with contextlib.suppress(Exception):
                callback()
        self._ui_queue_after_id = self.after(25, self._drain_ui_callbacks)

    def clear_dialog_content(self) -> None:
        """Destroy replaceable content while preserving the shared backdrop."""
        for widget in self.content_parent.winfo_children():
            widget.destroy()

    def _finalize_init(
        self,
        preferred_width: int = 800,
        preferred_height: int = 700,
        *,
        min_width: int = 500,
        min_height: int = 400,
        modal: bool = False,
    ) -> None:
        """Apply screen-aware geometry and reveal a fully constructed dialog."""
        self.apply_screen_aware_geometry(
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            min_width=min_width,
            min_height=min_height,
        )
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", False)
        if modal:
            self._previous_grab = self.grab_current()
            if self._previous_grab is self:
                self._previous_grab = None
            self.grab_set()

    def register_theme_refresh(self, callback: Callable[[], None]) -> None:
        """Refresh extra dialog-owned controls through the centralized listener."""
        self._theme_refresh_callbacks.append(callback)

    def _handle_dialog_theme_changed(self, appearance: str, color: str) -> None:
        if self._dialog_destroyed:
            return
        palette = resolve_palette(self._theme_manager)
        self.configure(fg_color=palette.background_mid)
        self._on_theme_changed(appearance, color)
        for callback in tuple(self._theme_refresh_callbacks):
            callback()

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        """Hook for dialog-specific controls; the shared shell is already updated."""

    def destroy(self) -> None:
        if self._dialog_destroyed:
            return
        self._dialog_destroyed = True
        if self._ui_queue_after_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._ui_queue_after_id)
            self._ui_queue_after_id = None
        with contextlib.suppress(Exception):
            if self.grab_current() is self:
                self.grab_release()
        if self._previous_grab is not None:
            with contextlib.suppress(Exception):
                if self._previous_grab.winfo_exists():
                    self._previous_grab.grab_set()
            self._previous_grab = None
        self._theme_manager.unsubscribe(
            ThemeEvent.THEME_CHANGED,
            self._handle_dialog_theme_changed,
        )
        super().destroy()
