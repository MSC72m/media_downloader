"""Icon-only button with tooltip and accessibility support."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IconButton(ctk.CTkButton):
    """Icon-only button with tooltip/accessibility label and focus styling."""

    def __init__(
        self,
        master,
        *,
        text: str = "",
        command: Callable[[], None] | None = None,
        tooltip: str | None = None,
        aria_label: str | None = None,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self._tooltip = tooltip or aria_label or text
        self._aria_label = aria_label or tooltip or text

        super().__init__(
            master,
            text=text,
            command=command,
            width=tokens.CONTROL_H,
            height=tokens.CONTROL_H,
            **kwargs,
        )

        self._apply_theme()
        self._setup_focus()
        self._setup_tooltip()

    def _apply_theme(self) -> None:
        """Apply semantic button colouring."""
        try:
            theme_json = self._theme_manager.get_theme_json()
            media = theme_json.get("MediaDownloader", {})
            accent = media.get(tokens.ACCENT_PRIMARY, "#007BFF")
            self.configure(fg_color=accent)
        except Exception as e:
            logger.debug(f"[ICON_BUTTON] Error applying theme: {e}")

    def _setup_focus(self) -> None:
        """Make button keyboard focusable with visible focus ring."""
        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_in(self, event: Any = None) -> None:
        """Highlight when focused."""
        try:
            theme_json = self._theme_manager.get_theme_json()
            media = theme_json.get("MediaDownloader", {})
            focus_color = media.get(tokens.FOCUS_RING, media.get(tokens.ACCENT_PRIMARY, "#007BFF"))
            self.configure(border_width=tokens.FOCUS_WIDTH, border_color=focus_color)
        except Exception:
            pass

    def _on_focus_out(self, event: Any = None) -> None:
        """Remove focus ring when blurred."""
        self.configure(border_width=0)

    def _setup_tooltip(self) -> None:
        """Add accessibility tooltip on hover."""
        self.bind("<Enter>", self._show_tooltip)
        self.bind("<Leave>", self._hide_tooltip)

    def _show_tooltip(self, event: Any = None) -> None:
        """Show tooltip (implementation deferred; can use Tk tooltip library)."""

    def _hide_tooltip(self, event: Any = None) -> None:
        """Hide tooltip."""

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_theme()

    def destroy(self) -> None:
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
