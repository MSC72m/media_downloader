from typing import Any

import customtkinter as ctk

from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, GradientButton, resolve_palette

from .base_dialog import BaseDialog


class CenteredInputDialog(BaseDialog):
    """Modal input dialog whose ``get_input`` call synchronously waits for a result."""

    def __init__(
        self,
        parent: Any,
        title: str,
        text: str,
        initial_value: str | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        super().__init__(parent, title=title, theme_manager=theme_manager)
        self._user_input: str | None = None
        self._input_var = ctk.StringVar(value=initial_value or "")

        self._create_widgets(text)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Return>", self._submit)
        self.bind("<Escape>", self._cancel)
        self._finalize_init(
            preferred_width=420,
            preferred_height=210,
            min_width=360,
            min_height=190,
            modal=True,
        )
        self.entry.focus_set()
        self.entry.icursor("end")

    def _create_widgets(self, text: str) -> None:
        palette = resolve_palette(self._theme_manager)
        self.card = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
        )
        self.card.pack(fill="both", expand=True, padx=20, pady=20)
        self.card.grid_columnconfigure(0, weight=1)

        self.prompt_label = ctk.CTkLabel(
            self.card,
            text=text,
            font=tokens.font("body"),
            text_color=palette.text,
            anchor="w",
        )
        self.prompt_label.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 8))

        self.entry = ctk.CTkEntry(
            self.card,
            textvariable=self._input_var,
            height=tokens.CONTROL_H_LG,
            font=tokens.font("body"),
            fg_color=palette.surface,
            border_color=palette.border_strong,
            text_color=palette.text,
        )
        self.entry.grid(row=1, column=0, sticky="ew", padx=20)

        button_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        button_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=18)
        button_frame.grid_columnconfigure((0, 1), weight=1)

        self.cancel_button = GlassButton(
            button_frame,
            text="Cancel",
            command=self._cancel,
            theme_manager=self._theme_manager,
            variant="secondary",
            height=tokens.CONTROL_H,
        )
        self.cancel_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.ok_button = GradientButton(
            button_frame,
            text="OK",
            command=self._submit,
            theme_manager=self._theme_manager,
            height=tokens.CONTROL_H,
        )
        self.ok_button.grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _submit(self, _event: Any = None) -> None:
        self._user_input = self._input_var.get()
        self.destroy()

    def _cancel(self, _event: Any = None) -> None:
        self._user_input = None
        self.destroy()

    def _on_theme_changed(self, _appearance: str, _color: str) -> None:
        palette = resolve_palette(self._theme_manager)
        self.prompt_label.configure(text_color=palette.text)
        self.entry.configure(
            fg_color=palette.surface,
            border_color=palette.border_strong,
            text_color=palette.text,
        )

    def get_input(self) -> str | None:
        """Wait for the modal dialog to close and return its submitted value."""
        self.wait_window(self)
        return self._user_input
