import math

import customtkinter as ctk

from ...core.enums.theme_event import ThemeEvent
from ...ui.utils.theme_manager import ThemeManager, get_theme_manager
from ...utils.window import WindowCenterMixin


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


class SmallLoadingSpinner(ctk.CTkToplevel, WindowCenterMixin):
    """Small, elegant loading spinner that centers itself."""

    def __init__(
        self,
        parent,
        message: str = "Loading...",
        size: int = 60,
        theme_manager: ThemeManager | None = None,
        **kwargs,
    ) -> None:
        ctk.CTkToplevel.__init__(self, parent, **kwargs)

        self.message = message
        self.size = size
        self.is_running = False
        self.angle = 0

        self._theme_manager = theme_manager or get_theme_manager()
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.configure(fg_color="transparent")
        self.overrideredirect(True)  # Remove window decorations
        self.attributes("-topmost", True)  # Keep on top

        self._create_spinner()

        self.withdraw()

    def _get_surface_color(self) -> str:
        """Get the current surface color as a single string for canvas bg."""
        colors = self._theme_manager.get_colors()
        return colors.get("surface", "#2b2b2b")

    def _get_accent_color(self) -> str:
        """Get the current accent color."""
        colors = self._theme_manager.get_colors()
        return colors.get("accent", "#3498db")

    def _get_accent_rgb(self) -> tuple[int, int, int]:
        """Get the accent color as an RGB tuple."""
        return _hex_to_rgb(self._get_accent_color())

    def _create_spinner(self) -> None:
        """Create the small spinner with message."""
        colors = self._theme_manager.get_colors()
        surface = colors.get("surface", "#2b2b2b")
        accent = colors.get("accent", "#3498db")
        text_on_surface = colors.get("text_on_surface", "#FFFFFF")

        self.container = ctk.CTkFrame(self, fg_color=surface, corner_radius=10)
        self.container.pack(expand=True)

        self.canvas = ctk.CTkCanvas(
            self.container,
            width=self.size,
            height=self.size,
            highlightthickness=0,
            bg=surface,
        )
        self.canvas.pack(pady=(15, 5))

        self.segments = []
        num_segments = 8
        radius = self.size * 0.3
        center = self.size / 2

        for i in range(num_segments):
            angle = (2 * math.pi / num_segments) * i

            x1 = center + (radius * 0.7) * math.cos(angle)
            y1 = center + (radius * 0.7) * math.sin(angle)
            x2 = center + radius * math.cos(angle)
            y2 = center + radius * math.sin(angle)

            segment = self.canvas.create_line(
                x1, y1, x2, y2, width=3, capstyle="round", fill=accent
            )
            self.segments.append((segment, angle))

        self.message_label = ctk.CTkLabel(
            self.container,
            text=self.message,
            font=("Roboto", 10),
            text_color=text_on_surface,
        )
        self.message_label.pack(pady=(0, 15))

    def start(self) -> None:
        """Start the spinner animation."""
        if not self.is_running:
            self.is_running = True
            self.lift()
            self._animate()

    def stop(self) -> None:
        """Stop the spinner animation."""
        self.is_running = False

    def _animate(self) -> None:
        """Animate the spinner rotation."""
        if not self.is_running:
            return

        self.angle = (self.angle + 15) % 360

        base_color = self._get_accent_rgb()

        for segment, base_angle in self.segments:
            angle_rad = math.radians(base_angle + self.angle)
            opacity = (math.sin(angle_rad) + 1) / 2  # Normalize to 0-1

            faded_color = tuple(int(c * opacity) for c in base_color)
            color = f"#{faded_color[0]:02x}{faded_color[1]:02x}{faded_color[2]:02x}"

            self.canvas.itemconfig(segment, fill=color)

        self.after(50, self._animate)

    def set_message(self, message: str) -> None:
        """Update the loading message."""
        self.message = message
        if hasattr(self, "message_label"):
            self.message_label.configure(text=message)

    def _safe_deiconify(self) -> None:
        """Safely deiconify the window, handling CustomTkinter race conditions."""
        try:
            self.update_idletasks()
            self.deiconify()
        except Exception:
            try:
                self.update()
                self.deiconify()
            except Exception:
                pass

    def show(self, parent=None) -> None:
        """Show the spinner centered on parent or screen."""
        if parent and hasattr(parent, "winfo_exists") and parent.winfo_exists():
            self.transient(parent)

        self.update_idletasks()

        self.center_window()

        self._safe_deiconify()  # Show the window
        self.lift()  # Bring to front
        self.grab_set()  # Make modal
        self.start()  # Start animation

    def hide(self) -> None:
        """Hide the spinner."""
        self.stop()
        self.withdraw()

    def destroy(self) -> None:
        """Clean up the spinner."""
        self.stop()
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()

    def _on_theme_changed(self, appearance, color) -> None:
        self._apply_theme_colors()

    def _apply_theme_colors(self) -> None:
        if not hasattr(self, "container"):
            return
        colors = self._theme_manager.get_colors()
        surface = colors.get("surface", "#2b2b2b")
        text_on_surface = colors.get("text_on_surface", "#FFFFFF")
        accent = colors.get("accent", "#3498db")

        self.container.configure(fg_color=surface)
        self.canvas.configure(bg=surface)
        self.message_label.configure(text_color=text_on_surface)

        for segment, _angle in self.segments:
            self.canvas.itemconfig(segment, fill=accent)


class LoadingOverlay(ctk.CTkFrame):
    """Simple full-page loading overlay for modal dialogs."""

    def __init__(
        self,
        parent,
        message: str = "Loading...",
        theme_manager: ThemeManager | None = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)

        self.message = message
        self.spinner: SmallLoadingSpinner | None = None

        self._theme_manager = theme_manager or get_theme_manager()
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_overlay_theme_changed)

        self._create_overlay()

    def _create_overlay(self) -> None:
        """Create the overlay with spinner."""
        self.grid(row=0, column=0, sticky="nsew")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        colors = self._theme_manager.get_colors()
        overlay_bg = colors.get("overlay_bg", "#1a1a1a")
        self.configure(fg_color=overlay_bg)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.spinner = SmallLoadingSpinner(
            self.winfo_toplevel(),
            message=self.message,
            size=50,
            theme_manager=self._theme_manager,
        )

    def start(self) -> None:
        """Start the loading animation."""
        if self.spinner:
            self.spinner.show(self.winfo_toplevel())

    def stop(self) -> None:
        """Stop the loading animation."""
        if self.spinner:
            self.spinner.hide()

    def set_message(self, message: str) -> None:
        """Update the loading message."""
        self.message = message
        if self.spinner:
            self.spinner.set_message(message)

    def show(self) -> None:
        """Show the overlay."""
        self.lift()
        self.start()

    def hide(self) -> None:
        """Hide the overlay."""
        self.stop()
        self.place_forget()

    def _on_overlay_theme_changed(self, appearance, color) -> None:
        colors = self._theme_manager.get_colors()
        overlay_bg = colors.get("overlay_bg", "#1a1a1a")
        self.configure(fg_color=overlay_bg)

    def destroy(self) -> None:
        """Clean up the overlay."""
        if self._theme_manager:
            self._theme_manager.unsubscribe(
                ThemeEvent.THEME_CHANGED, self._on_overlay_theme_changed
            )
        super().destroy()
