"""Shared base class for all media downloader dialogs.

Reduces the ~80-line boilerplate (theme subscription, geometry, centering,
window management) that YouTube and Spotify dialogs currently duplicate.
"""

from __future__ import annotations

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger
from src.utils.window import WindowCenterMixin

logger = get_logger(__name__)


class BaseDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Opinionated base for a downloader dialog.

    Subclasses call ``_finalize_init()`` after their own ``__init__``
    to apply geometry, centering, and theme wiring.
    """

    def __init__(
        self,
        parent,
        *,
        title: str = "Download",
        config: AppConfig | None = None,
        theme_manager: ThemeManager | None = None,
        preferred_width: int = 800,
        preferred_height: int = 700,
    ) -> None:
        super().__init__(parent)

        self._cfg = config or get_config()
        self._theme_manager = theme_manager or get_theme_manager()
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.title(title)
        self.transient(parent)
        self.resizable(True, True)
        self.withdraw()

    def _finalize_init(self, preferred_width: int = 800, preferred_height: int = 700) -> None:
        self.apply_screen_aware_geometry(
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            min_width=500,
            min_height=400,
        )
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", False)

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        pass

    def destroy(self) -> None:
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
