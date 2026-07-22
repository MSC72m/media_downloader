from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, resolve_palette


class PathEntryBar(GlassFrame):
    """Glass path-entry surface for directory navigation."""

    def __init__(
        self,
        master: Any,
        initial_path: str,
        on_path_change: Callable[[], None],
        theme_manager: ThemeManager | None = None,
    ) -> None:
        super().__init__(
            master,
            theme_manager=theme_manager,
            corner_radius=tokens.RADIUS_MD,
        )
        self.grid_columnconfigure(0, weight=1)

        self.path_var = ctk.StringVar(value=initial_path)
        palette = resolve_palette(self.theme_manager)

        self.entry = ctk.CTkEntry(
            self,
            textvariable=self.path_var,
            height=tokens.CONTROL_H_LG,
            font=tokens.font("body"),
            fg_color=palette.surface,
            border_color=palette.border_strong,
            text_color=palette.text,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=10)

        self.go_button = GlassButton(
            self,
            text="Go",
            width=64,
            command=on_path_change,
            theme_manager=self.theme_manager,
            variant="secondary",
            height=tokens.CONTROL_H_LG,
        )
        self.go_button.grid(row=0, column=1, padx=(6, 10), pady=10)

    def _handle_visual_theme_changed(self, appearance: str, color: str) -> None:
        super()._handle_visual_theme_changed(appearance, color)
        palette = resolve_palette(self.theme_manager)
        self.entry.configure(
            fg_color=palette.surface,
            border_color=palette.border_strong,
            text_color=palette.text,
        )

    def get_path(self) -> str:
        """Get current path."""
        return self.path_var.get()

    def set_path(self, path: str) -> None:
        """Set new path."""
        self.path_var.set(path)
