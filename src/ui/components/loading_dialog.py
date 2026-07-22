"""Shared visual-system loading dialog."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassFrame, resolve_palette
from src.utils.logger import get_logger

logger = get_logger(__name__)


class LoadingDialog(BaseDialog):
    """Modal loading dialog with cycling animated dots and a timeout."""

    def __init__(
        self,
        parent: Any,
        message: str = "Loading",
        timeout: int = 90,
        max_dots: int = 3,
        dot_animation_interval: int = 500,
        on_timeout: Callable[[], None] | None = None,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            parent,
            title="Loading",
            theme_manager=theme_manager,
            **kwargs,
        )

        self.message = message
        self.timeout = timeout
        self.max_dots = max_dots
        self.dot_animation_interval = dot_animation_interval
        self.on_timeout = on_timeout
        self.dot_count = 0
        self.is_running = False
        self._timeout_id: str | None = None
        self._animation_id: str | None = None

        self.resizable(False, False)
        self.overrideredirect(False)
        self._create_content()
        self._finalize_init(
            preferred_width=300,
            preferred_height=100,
            min_width=300,
            min_height=100,
            modal=True,
        )
        self.start_animation()

        if timeout > 0:
            self._timeout_id = self.after(timeout * 1000, self._timeout)

    def _create_content(self) -> None:
        """Create the loading dialog content on a shared glass surface."""
        palette = resolve_palette(self._theme_manager)
        main_frame = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
            corner_radius=12,
        )
        main_frame.pack(expand=True, fill="both", padx=16, pady=16)

        self.message_label = ctk.CTkLabel(
            main_frame,
            text=self.message,
            font=("Roboto", 14),
            text_color=palette.text,
        )
        self.message_label.pack(expand=True)

    def start_animation(self) -> None:
        """Start the dot animation."""
        if self.is_running:
            return
        self.is_running = True
        self._animate_dots()

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_theme_colors()

    def _apply_theme_colors(self) -> None:
        if hasattr(self, "message_label"):
            palette = resolve_palette(self._theme_manager)
            self.message_label.configure(text_color=palette.text)

    def _animate_dots(self) -> None:
        """Animate dots with cycling behavior."""
        if not self.is_running:
            self._animation_id = None
            return

        self.dot_count = (self.dot_count % self.max_dots) + 1
        self.message_label.configure(text=f"{self.message}{'.' * self.dot_count}")
        self._animation_id = self.after(self.dot_animation_interval, self._animate_dots)

    def stop_animation(self) -> None:
        """Stop the animation and cancel its pending callback."""
        self.is_running = False
        if self._animation_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._animation_id)
            self._animation_id = None

    def _timeout(self) -> None:
        """Close the dialog when its timeout expires."""
        self._timeout_id = None
        logger.info("[LOADING_DIALOG] Timeout reached, closing dialog")
        callback = self.on_timeout
        self.close()
        if callback is not None:
            callback()

    def close(self) -> None:
        """Close the dialog with proper cleanup."""
        logger.debug("[LOADING_DIALOG] close() called")
        try:
            self.destroy()
        except Exception as exc:
            logger.error(
                "[LOADING_DIALOG] Error in destroy(): %s",
                exc,
                exc_info=True,
            )

    def _release_grab(self) -> None:
        """Release this window's modal grab if active."""
        with contextlib.suppress(Exception):
            if self.grab_current() is self:
                self.grab_release()
                logger.debug("[LOADING_DIALOG] Grab released")

    def destroy(self) -> None:
        """Cancel callbacks and delegate shared lifecycle cleanup to BaseDialog."""
        if self._dialog_destroyed:
            return

        logger.debug("[LOADING_DIALOG] destroy() called")
        self.stop_animation()
        if self._timeout_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._timeout_id)
            self._timeout_id = None
        self._release_grab()
        super().destroy()
