"""Canonical surface aliases backed by the centralized visual system."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GlassFrame, resolve_palette


class BaseSurface(GlassFrame):
    def __init__(
        self,
        master,
        *,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            theme_manager=theme_manager,
            elevation="base",
            **kwargs,
        )


class RaisedSurface(GlassFrame):
    def __init__(
        self,
        master,
        *,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            theme_manager=theme_manager,
            elevation="raised",
            **kwargs,
        )


class OverlaySurface(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        *,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        super().__init__(master, **kwargs)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self._apply_palette()

    def _apply_palette(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self.configure(fg_color=palette.surface_raised)

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_palette()

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
