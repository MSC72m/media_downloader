"""Shared visual-system loading spinner components."""

from __future__ import annotations

import contextlib
import math
from typing import Any

import customtkinter as ctk

from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassFrame, resolve_palette


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string to an RGB tuple."""
    value = hex_color.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


class SmallLoadingSpinner(BaseDialog):
    """Small non-modal loading spinner that can be shown and hidden repeatedly."""

    def __init__(
        self,
        parent: Any,
        message: str = "Loading...",
        size: int = 60,
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
        self.size = size
        self.is_running = False
        self.angle = 0
        self._animation_id: str | None = None

        self.resizable(False, False)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self._create_spinner()

    def _get_surface_color(self) -> str:
        """Return the raised shared-surface color used by the canvas."""
        return resolve_palette(self._theme_manager).surface_raised

    def _get_accent_color(self) -> str:
        """Return the current shared accent color."""
        return resolve_palette(self._theme_manager).accent

    def _get_accent_rgb(self) -> tuple[int, int, int]:
        """Return the current accent color as RGB."""
        return _hex_to_rgb(self._get_accent_color())

    def _create_spinner(self) -> None:
        """Create the spinner and message on a shared glass surface."""
        palette = resolve_palette(self._theme_manager)
        self.container = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
            corner_radius=12,
        )
        self.container.pack(expand=True, fill="both", padx=6, pady=6)

        self.canvas = ctk.CTkCanvas(
            self.container,
            width=self.size,
            height=self.size,
            highlightthickness=0,
            bg=palette.surface_raised,
        )
        self.canvas.pack(pady=(15, 5))

        self.segments: list[tuple[int, float]] = []
        num_segments = 8
        radius = self.size * 0.3
        center = self.size / 2

        for index in range(num_segments):
            angle = (2 * math.pi / num_segments) * index
            x1 = center + (radius * 0.7) * math.cos(angle)
            y1 = center + (radius * 0.7) * math.sin(angle)
            x2 = center + radius * math.cos(angle)
            y2 = center + radius * math.sin(angle)
            segment = self.canvas.create_line(
                x1,
                y1,
                x2,
                y2,
                width=3,
                capstyle="round",
                fill=palette.accent,
            )
            self.segments.append((segment, angle))

        self.message_label = ctk.CTkLabel(
            self.container,
            text=self.message,
            font=("Roboto", 10),
            text_color=palette.text,
        )
        self.message_label.pack(pady=(0, 15), padx=15)

    def start(self) -> None:
        """Start the spinner animation."""
        if self.is_running:
            return
        self.is_running = True
        self.lift()
        self._animate()

    def stop(self) -> None:
        """Stop the spinner animation and cancel its pending callback."""
        self.is_running = False
        if self._animation_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._animation_id)
            self._animation_id = None

    def _animate(self) -> None:
        """Animate the spinner rotation."""
        if not self.is_running:
            self._animation_id = None
            return

        self.angle = (self.angle + 15) % 360
        base_color = self._get_accent_rgb()

        for segment, base_angle in self.segments:
            angle_rad = math.radians(base_angle + self.angle)
            opacity = (math.sin(angle_rad) + 1) / 2
            faded_color = tuple(int(channel * opacity) for channel in base_color)
            color = f"#{faded_color[0]:02x}{faded_color[1]:02x}{faded_color[2]:02x}"
            self.canvas.itemconfig(segment, fill=color)

        self._animation_id = self.after(50, self._animate)

    def set_message(self, message: str) -> None:
        """Update the loading message."""
        self.message = message
        self.message_label.configure(text=message)

    def _safe_deiconify(self) -> None:
        """Safely deiconify despite CustomTkinter window-state races."""
        try:
            self.update_idletasks()
            self.deiconify()
        except Exception:
            with contextlib.suppress(Exception):
                self.update()
                self.deiconify()

    def show(self, parent: Any | None = None) -> None:
        """Show the spinner centered on its parent and start animating."""
        if parent is not None and hasattr(parent, "winfo_exists") and parent.winfo_exists():
            self.transient(parent)

        self.update_idletasks()
        preferred_width = max(self.size + 42, self.message_label.winfo_reqwidth() + 42)
        preferred_height = self.size + 82
        self._finalize_init(
            preferred_width=preferred_width,
            preferred_height=preferred_height,
            min_width=preferred_width,
            min_height=preferred_height,
            modal=False,
        )
        self.attributes("-topmost", True)
        self.start()

    def hide(self) -> None:
        """Hide the spinner and stop animating."""
        self.stop()
        self.withdraw()

    def destroy(self) -> None:
        """Cancel animation and delegate shared lifecycle cleanup to BaseDialog."""
        if self._dialog_destroyed:
            return
        self.stop()
        super().destroy()

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_theme_colors()

    def _apply_theme_colors(self) -> None:
        if not hasattr(self, "container"):
            return
        palette = resolve_palette(self._theme_manager)
        self.canvas.configure(bg=palette.surface_raised)
        self.message_label.configure(text_color=palette.text)
        for segment, _angle in self.segments:
            self.canvas.itemconfig(segment, fill=palette.accent)


class LoadingOverlay(GlassFrame):
    """Embedded full-page glass overlay controlling a small loading spinner."""

    def __init__(
        self,
        parent: Any,
        message: str = "Loading...",
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            parent,
            theme_manager=theme_manager,
            elevation="raised",
            corner_radius=0,
            **kwargs,
        )
        self.message = message
        self.spinner: SmallLoadingSpinner | None = None
        self._overlay_destroyed = False
        self._create_overlay()

    def _create_overlay(self) -> None:
        """Place the embedded overlay and create its spinner."""
        palette = resolve_palette(self.theme_manager)
        self.configure(fg_color=palette.surface_raised, border_color=palette.border_strong)
        self.grid(row=0, column=0, sticky="nsew")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.spinner = SmallLoadingSpinner(
            self.winfo_toplevel(),
            message=self.message,
            size=50,
            theme_manager=self.theme_manager,
        )

    def start(self) -> None:
        """Start the loading animation."""
        if self.spinner is not None:
            self.spinner.show(self.winfo_toplevel())

    def stop(self) -> None:
        """Stop the loading animation."""
        if self.spinner is not None:
            self.spinner.hide()

    def set_message(self, message: str) -> None:
        """Update the loading message."""
        self.message = message
        if self.spinner is not None:
            self.spinner.set_message(message)

    def show(self) -> None:
        """Restore and raise the embedded overlay."""
        self.grid()
        self.lift()
        self.start()

    def hide(self) -> None:
        """Hide the embedded overlay and stop its spinner."""
        self.stop()
        self.grid_remove()

    def destroy(self) -> None:
        """Destroy the spinner and release GlassFrame's theme subscription."""
        if self._overlay_destroyed:
            return
        self._overlay_destroyed = True
        if self.spinner is not None:
            with contextlib.suppress(Exception):
                self.spinner.destroy()
            self.spinner = None
        super().destroy()
