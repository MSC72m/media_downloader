import customtkinter as ctk


class StatusBar(ctk.CTkFrame):
    """Status bar showing download progress and information."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create center frame for alignment
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=0, sticky="ew")
        self.center_frame.grid_columnconfigure(0, weight=1)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.center_frame,
            text="Ready",
            font=("Roboto", 12)
        )
        self.status_label.grid(row=0, column=0, pady=(5, 5))

        # Progress bar with increased width
        self.progress_bar = ctk.CTkProgressBar(
            self.center_frame,
            height=15,
            width=400  # Increased width
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=20)
        self.progress_bar.set(0)

    def show_message(self, message: str):
        """Show status message."""
        self.status_label.configure(text=message)

    def show_error(self, message: str):
        """Show error message."""
        self.status_label.configure(text=f"Error: {message}")

    def update_progress(self, progress: float):
        """Update progress display."""
        self.progress_bar.set(progress / 100)
        if progress >= 100:
            self.status_label.configure(text="Download Complete")
        else:
            self.status_label.configure(text=f"Downloading... {progress:.1f}%")

    def reset(self):
        """Reset status bar to initial state."""
        self.progress_bar.set(0)
        self.status_label.configure(text="Ready")