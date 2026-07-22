"""Reusable themed message and confirmation dialog."""

from __future__ import annotations

from typing import Any

import customtkinter as ctk

from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, GradientButton, resolve_palette

from .base_dialog import BaseDialog


class MessageDialog(BaseDialog):
    """A modal gradient/glass message window with one or two actions."""

    def __init__(
        self,
        parent: Any,
        *,
        title: str,
        heading: str,
        message: str,
        primary_text: str = "OK",
        secondary_text: str | None = None,
        theme_manager: ThemeManager | None = None,
        preferred_width: int = 560,
        preferred_height: int = 360,
    ) -> None:
        super().__init__(parent, title=title, theme_manager=theme_manager)
        self.result: bool | None = None

        palette = resolve_palette(self._theme_manager)
        self.card = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
        )
        self.card.pack(fill="both", expand=True, padx=20, pady=20)
        self.card.grid_columnconfigure(0, weight=1)
        self.card.grid_rowconfigure(1, weight=1)

        self.heading_label = ctk.CTkLabel(
            self.card,
            text=heading,
            font=tokens.font("title"),
            text_color=palette.text,
            anchor="w",
        )
        self.heading_label.grid(row=0, column=0, sticky="ew", padx=24, pady=(22, 10))

        self.message_label = ctk.CTkLabel(
            self.card,
            text=message,
            font=tokens.font("body"),
            text_color=palette.text_secondary,
            justify="left",
            anchor="nw",
            wraplength=max(300, preferred_width - 100),
        )
        self.message_label.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 16))

        actions = ctk.CTkFrame(self.card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="e", padx=24, pady=(0, 22))

        if secondary_text:
            self.secondary_button = GlassButton(
                actions,
                text=secondary_text,
                command=self._reject,
                theme_manager=self._theme_manager,
                variant="secondary",
                width=190,
                height=tokens.CONTROL_H,
            )
            self.secondary_button.pack(side="left", padx=(0, 8))

        self.primary_button = GradientButton(
            actions,
            text=primary_text,
            command=self._accept,
            theme_manager=self._theme_manager,
            width=150,
            height=tokens.CONTROL_H,
        )
        self.primary_button.pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._reject)
        self.bind("<Return>", self._accept)
        self.bind("<Escape>", self._reject)
        self._finalize_init(
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            min_width=420,
            min_height=260,
            modal=True,
        )

    def _accept(self, _event: Any = None) -> None:
        self.result = True
        self.destroy()

    def _reject(self, _event: Any = None) -> None:
        self.result = False
        self.destroy()

    def _on_theme_changed(self, _appearance: str, _color: str) -> None:
        palette = resolve_palette(self._theme_manager)
        self.heading_label.configure(text_color=palette.text)
        self.message_label.configure(text_color=palette.text_secondary)

    def get_result(self) -> bool:
        """Wait for the user and return whether the primary action was chosen."""
        self.wait_window(self)
        return self.result is True
