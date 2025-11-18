"""Simple loading dialog with animated dots."""

import customtkinter as ctk

from ...utils.window import WindowCenterMixin


class SimpleLoadingDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Simple loading dialog with animated dots."""

    def __init__(self, parent, message: str = "Loading", timeout: int = 90, **kwargs):
        super().__init__(parent, **kwargs)

        self.message = message
        self.timeout = timeout
        self.dot_count = 0
        self.max_dots = 60  # Max dots for 90 seconds (90 / 1.5 = 60)
        self.is_running = False

        # Configure window
        self.title("Loading")
        self.geometry("300x100")
        self.resizable(False, False)
        self.overrideredirect(False)  # Make it closable
        self.transient(parent)

        # Create content
        self._create_content()

        # Center the window
        self.center_window()

        # Update to ensure window is drawn
        self.update_idletasks()

        # Make visible and grab focus
        self.grab_set()
        self.focus_set()

        # Start animation
        self.start_animation()

        # Set timeout
        self.after(timeout * 1000, self._timeout)

    def _create_content(self):
        """Create the loading dialog content."""
        # Main frame
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Message label
        self.message_label = ctk.CTkLabel(
            main_frame,
            text=self.message,
            font=("Roboto", 14),
            text_color=("gray10", "gray90"),
        )
        self.message_label.pack(expand=True)

    def start_animation(self):
        """Start the dot animation."""
        self.is_running = True
        self._animate_dots()

    def _animate_dots(self):
        """Animate the dots."""
        if not self.is_running:
            return

        # Add one dot at a time, up to max_dots
        if self.dot_count < self.max_dots:
            self.dot_count += 1

        # Create dots string
        dots = "." * self.dot_count
        self.message_label.configure(text=f"{self.message}{dots}")

        # Schedule next frame (every 1.5 seconds for double speed)
        self.after(1500, self._animate_dots)

    def stop_animation(self):
        """Stop the animation."""
        self.is_running = False

    def _timeout(self):
        """Handle timeout."""
        self.stop_animation()
        self.destroy()

    def close(self):
        """Close the dialog."""
        self.stop_animation()
        self.destroy()

    def destroy(self):
        """Clean up the dialog."""
        self.stop_animation()
        super().destroy()
