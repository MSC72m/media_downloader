"""Compact settings drawer using the canonical glass visual system."""

from __future__ import annotations

import contextlib
from typing import Any

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.theme_event import ThemeEvent
from src.ui.components.concurrent_downloads_selector import ConcurrentDownloadsSelector
from src.ui.components.modern_surface import RaisedSurface
from src.ui.components.theme_switcher import ThemeSwitcher
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.ui.visual_system import GlassButton, GlassFrame, resolve_palette
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsPanel(RaisedSurface):
    """Right-side settings surface matching header, queue, and footer."""

    def __init__(
        self,
        master,
        *,
        theme_manager: ThemeManager | None = None,
        config: AppConfig | None = None,
        **kwargs: Any,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._config = config or get_config()
        self._is_open = False
        self._initial_focus = None
        self._themed_labels: list[tuple[Any, str]] = []
        super().__init__(
            master,
            theme_manager=self._theme_manager,
            width=306,
            corner_radius=14,
            **kwargs,
        )
        self.grid_propagate(False)
        self._build_ui()
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self.bind("<Escape>", lambda _event: self.close())
        self.grid_remove()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=13, pady=(12, 7))
        header.grid_columnconfigure(0, weight=1)

        palette = resolve_palette(self._theme_manager)
        self._title = ctk.CTkLabel(
            header,
            text="Settings",
            font=("Roboto", 14, "bold"),
            text_color=palette.text,
            anchor="w",
        )
        self._title.grid(row=0, column=0, sticky="w")
        self._themed_labels.append((self._title, "text"))

        close_button = GlassButton(
            header,
            text="Close",
            width=54,
            height=28,
            variant="ghost",
            command=self.close,
            theme_manager=self._theme_manager,
        )
        close_button.grid(row=0, column=1, sticky="e")

        content = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
        )
        content.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 9))

        appearance = self._create_section(content, "Appearance")
        ThemeSwitcher(appearance, self._theme_manager).pack(fill="x", padx=10, pady=(2, 10))

        downloads = self._create_section(content, "Downloads")
        ConcurrentDownloadsSelector(
            downloads,
            theme_manager=self._theme_manager,
            config=self._config,
        ).pack(fill="x", padx=10, pady=(2, 10))

        storage = self._create_section(content, "Storage")
        storage_hint = ctk.CTkLabel(
            storage,
            text=str(self._config.paths.downloads_dir),
            font=("Roboto", 10, "normal"),
            text_color=palette.text_muted,
            anchor="w",
            wraplength=245,
        )
        storage_hint.pack(fill="x", padx=10, pady=(2, 10))
        self._themed_labels.append((storage_hint, "muted"))

    def _create_section(self, parent: Any, title: str) -> GlassFrame:
        section = GlassFrame(
            parent,
            theme_manager=self._theme_manager,
            elevation="base",
            corner_radius=11,
        )
        section.pack(fill="x", pady=(0, 7))
        palette = resolve_palette(self._theme_manager)
        label = ctk.CTkLabel(
            section,
            text=title,
            font=("Roboto", 11, "bold"),
            text_color=palette.text_secondary,
            anchor="w",
        )
        label.pack(fill="x", padx=10, pady=(9, 2))
        self._themed_labels.append((label, "secondary"))
        return section

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        palette = resolve_palette(self._theme_manager)
        colors = {
            "text": palette.text,
            "secondary": palette.text_secondary,
            "muted": palette.text_muted,
        }
        for label, role in self._themed_labels:
            label.configure(text_color=colors[role])

    def open(self) -> None:
        if self._is_open:
            return
        self._initial_focus = self.winfo_toplevel().focus_get()
        self.grid(
            row=0,
            column=1,
            rowspan=4,
            sticky="nsew",
            padx=(0, 14),
            pady=14,
        )
        self._is_open = True
        self.focus_set()
        logger.debug("[SETTINGS_PANEL] Opened")

    def close(self) -> None:
        if not self._is_open:
            return
        self.grid_remove()
        self._is_open = False
        if self._initial_focus:
            with contextlib.suppress(Exception):
                self._initial_focus.focus_set()
        logger.debug("[SETTINGS_PANEL] Closed")

    def toggle(self) -> None:
        self.close() if self._is_open else self.open()

    def destroy(self) -> None:
        self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
