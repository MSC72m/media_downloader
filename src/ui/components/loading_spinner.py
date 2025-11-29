import math

import customtkinter as ctk

from ...utils.window import WindowCenterMixin


class SmallLoadingSpinner(ctk.CTkToplevel, WindowCenterMixin):
    """Small, elegant loading spinner that centers itself."""

    def __init__(self, parent, message: str = "Loading...", size: int = 60, **kwargs):
        ctk.CTkToplevel.__init__(self, parent, **kwargs)

        self.message = message
        self.size = size
        self.is_running = False
        self.angle = 0

        self.configure(fg_color="transparent")
        self.overrideredirect(True)  # Remove window decorations
        self.attributes("-topmost", True)  # Keep on top

        self._create_spinner()

        self.place_forget()

    def _create_spinner(self):
        """Create the small spinner with message."""
        container = ctk.CTkFrame(self, fg_color=("#2b2b2b", "#f0f0f0"), corner_radius=10)
        container.pack(expand=True)

        self.canvas = ctk.CTkCanvas(
            container,
            width=self.size,
            height=self.size,
            highlightthickness=0,
            bg="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0",
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
                x1, y1, x2, y2, width=3, capstyle="round", fill="#3498db"
            )
            self.segments.append((segment, angle))

        self.message_label = ctk.CTkLabel(
            container,
            text=self.message,
            font=("Roboto", 10),
            text_color=("#ffffff", "#000000"),
        )
        self.message_label.pack(pady=(0, 15))

    def start(self):
        """Start the spinner animation."""
        if not self.is_running:
            self.is_running = True
            self.lift()
            self._animate()

    def stop(self):
        """Stop the spinner animation."""
        self.is_running = False

    def _animate(self):
        """Animate the spinner rotation."""
        if not self.is_running:
            return

        self.angle = (self.angle + 15) % 360

        for segment, base_angle in self.segments:
            angle_rad = math.radians(base_angle + self.angle)
            opacity = (math.sin(angle_rad) + 1) / 2  # Normalize to 0-1

            base_color = (52, 152, 219)  # #3498db
            faded_color = tuple(int(c * opacity) for c in base_color)
            color = f"#{faded_color[0]:02x}{faded_color[1]:02x}{faded_color[2]:02x}"

            self.canvas.itemconfig(segment, fill=color)

        self.after(50, self._animate)

    def set_message(self, message: str):
        """Update the loading message."""
        self.message = message
        if hasattr(self, "message_label"):
            self.message_label.configure(text=message)

    def _safe_deiconify(self):
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

    def show(self, parent=None):
        """Show the spinner centered on parent or screen."""
        if parent and hasattr(parent, "winfo_exists") and parent.winfo_exists():
            self.transient(parent)

        self.update_idletasks()

        self.center_window()

        self._safe_deiconify()  # Show the window
        self.lift()  # Bring to front
        self.grab_set()  # Make modal
        self.start()  # Start animation

    def hide(self):
        """Hide the spinner."""
        self.stop()
        self.withdraw()

    def destroy(self):
        """Clean up the spinner."""
        self.stop()
        super().destroy()


class LoadingOverlay(ctk.CTkFrame):
    """Simple full-page loading overlay for modal dialogs."""

    def __init__(self, parent, message: str = "Loading...", **kwargs):
        super().__init__(parent, **kwargs)

        self.message = message
        self.spinner: SmallLoadingSpinner | None = None

        self._create_overlay()

    def _create_overlay(self):
        """Create the overlay with spinner."""
        self.grid(row=0, column=0, sticky="nsew")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)

        self.configure(fg_color=("#1a1a1a", "#f0f0f0"))

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.place(relx=0.5, rely=0.5, anchor="center")

        self.spinner = SmallLoadingSpinner(content_frame, message=self.message, size=50)
        self.spinner.pack()

    def start(self):
        """Start the loading animation."""
        if self.spinner:
            self.spinner.start()

    def stop(self):
        """Stop the loading animation."""
        if self.spinner:
            self.spinner.stop()

    def set_message(self, message: str):
        """Update the loading message."""
        self.message = message
        if self.spinner:
            self.spinner.set_message(message)

    def show(self):
        """Show the overlay."""
        self.lift()
        self.start()

    def hide(self):
        """Hide the overlay."""
        self.stop()
        self.place_forget()
