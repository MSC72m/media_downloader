import tkinter as tk


class WindowCenterMixin:
    """Mixin class to provide window centering functionality."""

    def center_window(self) -> None:
        """Center the window on the screen or relative to parent."""
        if not isinstance(self, tk.Tk) and not isinstance(self, tk.Toplevel):
            raise TypeError(
                "WindowCenterMixin must be used with Tk or Toplevel windows"
            )

        # Update window geometry to get accurate dimensions
        try:
            self.update_idletasks()
        except Exception:
            # Handle CustomTkinter dimension event bug
            pass

        # Get window size
        try:
            window_width = self.winfo_width()
            window_height = self.winfo_height()
        except Exception:
            # If we can't get dimensions, use defaults from geometry string
            window_width = 700
            window_height = 900

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # If window has parent, center relative to parent
        if hasattr(self, "master") and self.master and self.master.winfo_exists():
            parent = self.master
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            x = parent_x + (parent_width - window_width) // 2
            y = parent_y + (parent_height - window_height) // 2
        else:
            # Center on screen
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

        # Ensure window is fully visible
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))

        # Set the position
        self.geometry(f"+{x}+{y}")
