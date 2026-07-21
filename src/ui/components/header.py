"""Compact header using the same surface language as queue and footer."""

from __future__ import annotations

import customtkinter as ctk

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, Palette, resolve_palette


class AppHeader(GlassFrame):
    def __init__(
        self,
        master,
        theme_manager: ThemeManager,
        config,
        *,
        title: str = "Media Downloader",
    ) -> None:
        self._theme_manager = theme_manager
        super().__init__(
            master,
            theme_manager=theme_manager,
            elevation="base",
            corner_radius=13,
            height=44,
        )
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self.grid_columnconfigure(1, weight=1)

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="w", padx=(13, 0), pady=7)

        self.title_label = ctk.CTkLabel(
            brand,
            text=title,
            font=("Roboto", 14, "bold"),
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self._count_label = ctk.CTkLabel(
            brand,
            text="Queue empty",
            font=("Roboto", 10, "normal"),
            anchor="w",
        )
        self._count_label.grid(row=0, column=1, padx=(11, 0), sticky="w")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=0, column=2, sticky="e", padx=7, pady=6)

        self.appearance_button = GlassButton(
            controls,
            text="Light" if theme_manager.get_appearance() == AppearanceMode.DARK else "Dark",
            width=58,
            height=30,
            variant="ghost",
            command=self._toggle_appearance,
            theme_manager=theme_manager,
        )
        self.appearance_button.grid(row=0, column=0, padx=(0, 3))

        self.settings_button = GlassButton(
            controls,
            text="Settings",
            width=70,
            height=30,
            variant="ghost",
            command=None,
            theme_manager=theme_manager,
        )
        self.settings_button.grid(row=0, column=1)
        self._apply_palette(resolve_palette(theme_manager))

    def _toggle_appearance(self) -> None:
        current = self._theme_manager.get_appearance()
        appearance = AppearanceMode.LIGHT if current == AppearanceMode.DARK else AppearanceMode.DARK
        self._theme_manager.set_theme(appearance, self._theme_manager.get_color_theme())

    def set_count(self, active: int, total: int) -> None:
        if total == 0:
            text = "Queue empty"
        elif active:
            text = f"{active} active · {total} total"
        else:
            text = f"{total} in queue"
        self._count_label.configure(text=text)

    def _apply_palette(self, palette: Palette) -> None:
        self.title_label.configure(text_color=palette.text)
        self._count_label.configure(text_color=palette.text_muted)
        self.appearance_button.configure(text="Light" if palette.appearance == "dark" else "Dark")

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_palette(resolve_palette(self._theme_manager))

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
