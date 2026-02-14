from __future__ import annotations

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.concurrent_option import ConcurrentOption
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ConcurrentDownloadsSelector(ctk.CTkFrame):
    def __init__(
        self,
        master,
        theme_manager: ThemeManager | None = None,
        config: AppConfig = get_config(),
    ) -> None:
        super().__init__(master, fg_color="transparent")

        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._config = config
        self._current_value = self._config.downloads.max_concurrent_downloads

        self.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, sticky="e")

        self.label = ctk.CTkLabel(
            container,
            text="Concurrency:",
            font=("Roboto", 11),
        )
        self.label.grid(row=0, column=0, padx=(0, 5), sticky="w")

        values = ConcurrentOption.all_options()
        self.dropdown = ctk.CTkComboBox(
            container,
            values=values,
            command=self._on_change,
            font=("Roboto", 11),
            width=70,
            height=30,
            dropdown_font=("Roboto", 11),
        )
        self.dropdown.set(str(self._current_value))
        self.dropdown.grid(row=0, column=1, padx=(0, 0))

        self._make_combobox_readonly()
        self._apply_theme_colors()

        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

    def _make_combobox_readonly(self) -> None:
        def prevent_edit(event) -> str | None:
            if event.keysym not in ("Return", "Escape", "Up", "Down"):
                return "break"
            return None

        def prevent_selection(_event) -> str:
            return "break"

        try:
            entry = self.dropdown._entry
            entry.bind("<Key>", prevent_edit)
            entry.bind("<Button-1>", lambda _e: self.dropdown._open_dropdown_menu())
            entry.bind("<Control-a>", prevent_selection)
            entry.bind("<Button-3>", prevent_selection)
        except Exception:
            pass

    def _apply_theme_colors(self) -> None:
        theme_json = self._theme_manager.get_theme_json()

        if button_config := theme_json.get("CTkButton", {}):
            button_color = button_config.get("fg_color")
            hover_color = button_config.get("hover_color")
            border_color = button_config.get("button_border_color") or button_color

            if isinstance(button_color, tuple):
                button_color = button_color[0] if isinstance(button_color[0], str) else button_color
            if isinstance(hover_color, tuple):
                hover_color = hover_color[0] if isinstance(hover_color[0], str) else hover_color
            if isinstance(border_color, tuple):
                border_color = border_color[0] if isinstance(border_color[0], str) else border_color

            self.dropdown.configure(
                fg_color=button_color,
                border_color=border_color,
                button_color=button_color,
                button_hover_color=hover_color,
            )

        if entry_config := theme_json.get("CTkEntry", {}):
            fg_color = entry_config.get("fg_color")
            border_color = entry_config.get("border_color")

            if isinstance(fg_color, tuple):
                fg_color = fg_color[0] if isinstance(fg_color[0], str) else fg_color
            if isinstance(border_color, tuple):
                border_color = border_color[0] if isinstance(border_color[0], str) else border_color

            self.dropdown.configure(
                fg_color=fg_color,
                border_color=border_color,
            )

        if label_config := theme_json.get("CTkLabel", {}):
            text_color = label_config.get("text_color")
            if isinstance(text_color, tuple):
                text_color = text_color[0] if isinstance(text_color[0], str) else text_color
            self.label.configure(text_color=text_color)

    def _on_theme_changed(self, appearance, color) -> None:
        self._apply_theme_colors()

    def _on_change(self, value: str) -> None:
        try:
            concurrent_value = int(value)
            self._config.downloads.max_concurrent_downloads = concurrent_value
            self._config.save_to_file()
            logger.info(f"[CONCURRENT_SELECTOR] Changed to {concurrent_value} concurrent downloads")
        except ValueError:
            logger.error(f"[CONCURRENT_SELECTOR] Invalid value: {value}")
